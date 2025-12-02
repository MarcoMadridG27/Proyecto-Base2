# multimedia_routes.py
from fastapi import UploadFile, File, Form
from typing import Optional
import os
import shutil
import time
import zipfile
import numpy as np
import csv
import re
import ast
import json
import librosa
import heapq

from src.multimedia_search.feature_extractor import FeatureExtractor
from src.multimedia_search.codebook import Codebook
from src.multimedia_search.knn_index import KNNIndex
from src.multimedia_search.visual_inverted_index import VisualInvertedIndex
from src.multimedia_search.knn_sequential_audio import KNNSequentialAudio  # keep for image multimodal compatibility
from src.multimedia_search.knn_index_audio import KNNIndexAudio

# Global multimedia instances
mm_extractor = FeatureExtractor()
mm_codebook: Optional[Codebook] = None
mm_index: Optional[KNNIndex] = None
mm_inverted_index: Optional[VisualInvertedIndex] = None

# Add global instance for audio codebook
mm_codebook_audio: Optional[Codebook] = None

# Almacena los descriptores por frame para cada audio (lista de arrays (frames, dim))
# Now we will use 10 frames x 13 MFCC per audio in CSV 'descriptors' field (light CSV)
audio_descriptors_list = []      # used for index-building (Codebook.train, KNNIndexAudio.build_index)
audio_index_paths = []           # lista de rutas (absolute or relative to media/)
# Almacena histograms (TF-IDF normalizados) para búsqueda secuencial
audio_histograms = []            # list of 1D np.arrays (vocab_size,)
# KNN helpers
knn_sequential_audio: Optional[object] = None
knn_index_audio: Optional[KNNIndexAudio] = None


def l2_normalize_vec(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-12
    return v / n


# ---------------------------
# AUDIO: extractor adapted to 10 frames x 13 MFCC
# ---------------------------
def extract_audio_features(filepath: str, n_mfcc: int = 10, n_frames: int = 40):

    try:
        y, sr = librosa.load(filepath, sr=None)
        if y is None or len(y) == 0:
            return None
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)  # (n_mfcc, frames)
        total_frames = mfcc.shape[1]
        if total_frames < n_frames:
            # pad by wrapping to ensure we always have n_frames
            mfcc = np.pad(mfcc, ((0, 0), (0, n_frames - total_frames)), mode='wrap')
            total_frames = n_frames
        indices = np.linspace(0, total_frames - 1, n_frames, dtype=int)
        selected = mfcc[:, indices]  # shape (n_mfcc, n_frames)
        return selected.T.astype(np.float32)  # (n_frames, n_mfcc)
    except Exception as e:
        print(f"[extract_audio_features] Error extracting MFCC from {filepath}: {e}")
        return None


def _parse_vector_string(s: str):
    """Robust parser for vectors like '[1.23 4.136 -7.8]' or '[1.0,2.0,...]'"""
    # Limpia saltos de línea y espacios extra
    s = s.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ').strip()
    # Elimina comillas si existen
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # Busca números con regex
    vals = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if not vals:
        return None
    arr = np.array([float(x) for x in vals], dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def register_multimedia_routes(app, DATA_DIR):
    """Register multimedia search endpoints to the FastAPI app"""

    # Mount static files for serving images
    from fastapi.staticfiles import StaticFiles
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

    @app.post("/multimedia/build_index")
    def build_multimedia_index(
        file: UploadFile = File(...),
        k: int = Form(100),
        index_name: str = Form("default"),
        use_tfidf: bool = Form(True)
    ):

        global mm_codebook, mm_index, mm_inverted_index

        try:
            # Setup directories
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")
            media_dir = os.path.join(base_dir, "media")
            os.makedirs(media_dir, exist_ok=True)

            # Save and extract ZIP
            zip_path = os.path.join(base_dir, "media.zip")
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(media_dir)

            # Find all media files (images and audio)
            media_files = []
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')

            for root, _, files in os.walk(media_dir):
                for f in files:
                    if f.lower().endswith(image_extensions + audio_extensions):
                        media_files.append(os.path.join(root, f))

            if not media_files:
                return {"ok": False, "error": "No images or audio found in ZIP"}

            # 1. Extract Features
            start_time = time.time()
            print(f"Extracting features from {len(media_files)} files...")

            descriptors_list = []
            valid_paths = []
            total_files = len(media_files)
            for i, path in enumerate(media_files):
                if i % 100 == 0:
                    print(f"Processing file {i+1}/{total_files}: {os.path.basename(path)}")

                if path.lower().endswith(image_extensions):
                    desc = mm_extractor.extract_image_features(path)
                elif path.lower().endswith(audio_extensions):
                    # For audio inside this general build, extract 10-frame descriptors
                    desc = extract_audio_features(path, n_mfcc=10, n_frames=40)
                else:
                    continue

                if desc is not None:
                    descriptors_list.append(desc)
                    valid_paths.append(path)

            if not descriptors_list:
                return {"ok": False, "error": "Could not extract features from any file"}

            # 2. Train Codebook
            print(f"Training codebook with k={k}...")
            mm_codebook = Codebook(k=k)
            mm_codebook.train(descriptors_list)

            # 3. Compute histograms for all files (without TF-IDF first)
            print("Computing histograms...")
            all_histograms = []
            for desc in descriptors_list:
                hist = mm_codebook.compute_histogram(desc, use_tfidf=False)
                all_histograms.append(hist)

            # 4. Build IDF if using TF-IDF
            if use_tfidf:
                print("Building IDF weights...")
                mm_codebook.build_idf(all_histograms)
                # Recompute histograms with TF-IDF
                all_histograms = []
                for desc in descriptors_list:
                    hist = mm_codebook.compute_histogram(desc, use_tfidf=True)
                    all_histograms.append(hist)

            # Normalize histograms (L2) for cosine similarity where appropriate
            all_histograms = [l2_normalize_vec(h) for h in all_histograms]

            # Save codebook
            mm_codebook.save(os.path.join(base_dir, "codebook.pkl"))

            # 13. Build KNN Sequential Index (generic multimodal index)
            print("Building KNN sequential index...")
            mm_index = KNNIndex(index_dir=base_dir)
            for idx, (path, hist) in enumerate(zip(valid_paths, all_histograms)):
                mm_index.add_vector(idx + 1, hist, path)
            mm_index.save()

            # 6. Build Inverted Index
            print("Building inverted index...")
            mm_inverted_index = VisualInvertedIndex(index_dir=base_dir)
            for idx, (path, hist) in enumerate(zip(valid_paths, all_histograms)):
                mm_inverted_index.add_document(idx + 1, hist, path)
            mm_inverted_index.save("inverted_index")

            build_time = time.time() - start_time

            return {
                "ok": True,
                "message": "Multimedia index built successfully",
                "stats": {
                    "num_files": len(media_files),
                    "indexed_files": len(valid_paths),
                    "vocabulary_size": k,
                    "use_tfidf": use_tfidf,
                    "build_time_seconds": build_time
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    @app.post("/multimedia/search")
    def search_multimedia(
        file: UploadFile = File(...),
        top_k: int = Form(13),
        index_name: str = Form("default")
    ):
        """
        Search for similar images using an uploaded query image.
        """
        global mm_codebook, mm_index

        try:
            # Load index if needed
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")

            if mm_codebook is None:
                try:
                    mm_codebook = Codebook()
                    mm_codebook.load(os.path.join(base_dir, "codebook.pkl"))
                except Exception:
                    return {"ok": False, "error": "Index not loaded/found. Build index first."}

            if mm_index is None:
                try:
                    mm_index = KNNIndex(index_dir=base_dir)
                    mm_index.load()
                except Exception:
                    return {"ok": False, "error": "Index not loaded/found. Build index first."}

            # Save query file temporarily
            temp_path = os.path.join(DATA_DIR, f"temp_query_{file.filename}")
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Process query - detect file type
            start_time = time.time()

            # Detect if image or audio
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')

            if temp_path.lower().endswith(image_extensions):
                desc = mm_extractor.extract_image_features(temp_path)
            elif temp_path.lower().endswith(audio_extensions):
                desc = extract_audio_features(temp_path, n_mfcc=10, n_frames=40)
            else:
                os.remove(temp_path)
                return {"ok": False, "error": "Unsupported file type. Use image or audio files."}

            if desc is None:
                os.remove(temp_path)
                return {"ok": False, "error": "Could not extract features from query image"}

            hist = mm_codebook.compute_histogram(desc)
            print(f"Query histogram sum: {np.sum(hist)}")
            print(f"Query histogram non-zero elements: {np.count_nonzero(hist)}")

            results = mm_index.search_sequential(hist, k=top_k)
            print(f"Found {len(results)} results")

            search_time = time.time() - start_time

            # Clean up
            os.remove(temp_path)

            # Format results
            formatted_results = []
            for rank, (dist, doc_id, path) in enumerate(results, 1):
                # Get relative path from media directory
                try:
                    # path is absolute, we need relative from media_dir
                    media_dir_path = os.path.join(DATA_DIR, f"mm_index_{index_name}", "media")
                    relative_path = os.path.relpath(path, media_dir_path)
                    # Replace backslashes with forward slashes for URLs
                    relative_path = relative_path.replace('\\', '/')
                except:
                    # Fallback to just filename
                    relative_path = os.path.basename(path)

                # Calculate similarity percentage
                similarity = max(0.0, 1.0 - float(dist))

                formatted_results.append({
                    "rank": rank,
                    "doc_id": doc_id,
                    "filename": relative_path,
                    "distance": float(dist),
                    "similarity": similarity
                })

            return {
                "ok": True,
                "results": formatted_results,
                "search_time_seconds": search_time
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    @app.post("/multimedia/compare_methods")
    def compare_search_methods(
        file: UploadFile = File(...),
        top_k: int = Form(13),
        index_name: str = Form("default")
    ):

        global mm_codebook, mm_index, mm_inverted_index

        try:
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")

            # Load indexes if needed
            if mm_codebook is None:
                mm_codebook = Codebook()
                mm_codebook.load(os.path.join(base_dir, "codebook.pkl"))

            if mm_index is None:
                mm_index = KNNIndex(index_dir=base_dir)
                mm_index.load()

            if mm_inverted_index is None:
                mm_inverted_index = VisualInvertedIndex(index_dir=base_dir)
                mm_inverted_index.load("inverted_index")

            # Save and process query
            temp_path = os.path.join(DATA_DIR, f"temp_query_{file.filename}")
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Detect if image or audio
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')

            if temp_path.lower().endswith(image_extensions):
                desc = mm_extractor.extract_image_features(temp_path)
            elif temp_path.lower().endswith(audio_extensions):
                desc = extract_audio_features(temp_path, n_mfcc=10, n_frames=40)
            else:
                os.remove(temp_path)
                return {"ok": False, "error": "Unsupported file type"}

            if desc is None:
                os.remove(temp_path)
                return {"ok": False, "error": "Could not extract features"}

            use_tfidf = mm_codebook.idf is not None
            hist = mm_codebook.compute_histogram(desc, use_tfidf=use_tfidf)

            # Method 1: Sequential KNN
            start_seq = time.time()
            results_seq = mm_index.search_sequential(hist, k=top_k)
            time_seq = time.time() - start_seq

            # Method 2: Inverted Index
            start_inv = time.time()
            results_inv = mm_inverted_index.search(hist, k=top_k)
            time_inv = time.time() - start_inv

            os.remove(temp_path)

            # Helper to get relative path
            def get_rel_path(abs_path):
                try:
                    media_dir_path = os.path.join(DATA_DIR, f"mm_index_{index_name}", "media")
                    rel = os.path.relpath(abs_path, media_dir_path)
                    return rel.replace('\\', '/')
                except:
                    return os.path.basename(abs_path)

            return {
                "ok": True,
                "sequential": {
                    "time_seconds": time_seq,
                    "results": [{"rank": i+1, "doc_id": doc_id, "filename": get_rel_path(path), "distance": float(dist), "similarity": max(0.0, 1.0 - float(dist))} 
                               for i, (dist, doc_id, path) in enumerate(results_seq)]
                },
                "indexed": {
                    "time_seconds": time_inv,
                    "results": [{"rank": i+1, "doc_id": doc_id, "filename": get_rel_path(path), "similarity": float(sim)} 
                               for i, (doc_id, sim, path) in enumerate(results_inv)]
                },
                "speedup": time_seq / time_inv if time_inv > 0 else 0
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    # -----------------------
    # AUDIO-SPECIFIC ENDPOINTS
    # -----------------------
    @app.post("/multimedia/audio/build_index")
    def build_audio_index(
        file: Optional[UploadFile] = File(None),
        k: int = Form(130),
        index_name: str = Form("default"),
        use_tfidf: bool = Form(True),
        csv_encoding: str = Form("utf-8"),
        use_server_csv: bool = Form(False),
    ):
        """
        Builds an audio index using frame-level MFCC descriptors (one entry per audio file).
        Steps:
         - Expect CSV that lists audio filenames (relative to base_dir/media) OR use all audio files in media folder
         - For each audio -> extract frame-level descriptors (frames, n_mfcc)
         - Train codebook on stacked descriptors
         - Compute histograms (TF or TF-IDF) for each audio
         - Save codebook & keep descriptors/histograms in memory for search
         - Build KNNIndexAudio (inverted index) for the 'index' method
        """
        global audio_descriptors_list, audio_index_paths, audio_histograms
        global mm_codebook_audio, knn_index_audio, knn_sequential_audio

        try:
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")
            media_dir = os.path.join(base_dir, "media")
            os.makedirs(media_dir, exist_ok=True)

            csv_path = os.path.join(base_dir, "audio_dataset.csv")

            # If file uploaded -> save; else if use_server_csv -> expect csv already at csv_path
            mp3_list = []
            if file is not None:
                print(f"[AUDIO BUILD] Uploading CSV file...")
                with open(csv_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            else:
                if not (use_server_csv and os.path.exists(csv_path)):
                    # no CSV -> fallback to using all audio files in media_dir
                    print("[AUDIO BUILD] No CSV provided; scanning media directory for audio files.")
                else:
                    print(f"[AUDIO BUILD] Using server CSV from: {csv_path}")

            # If CSV exists, parse list of files from it (column names: mp3, file, audio, mp3_path)
            if os.path.exists(csv_path):
                print(f"[AUDIO BUILD] Parsing CSV from: {csv_path}")
                with open(csv_path, "r", encoding=csv_encoding, errors="ignore") as fh:
                    reader = csv.DictReader(fh, delimiter=",")
                    for row_idx, row in enumerate(reader):
                        mp3_field = row.get("mp3") or row.get("mp3_path") or row.get("audio") or row.get("file")
                        if mp3_field and str(mp3_field).strip():
                            mp3_list.append(str(mp3_field).strip())

            # If mp3_list empty => scan media_dir for audio files
            if not mp3_list:
                audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
                for root, _, files in os.walk(media_dir):
                    for f in files:
                        if f.lower().endswith(audio_extensions):
                            rel = os.path.relpath(os.path.join(root, f), media_dir)
                            mp3_list.append(rel)

            if not mp3_list:
                return {"ok": False, "error": f"No audio files found in media dir ({media_dir}) and no CSV entries provided."}

            # 1) Extract frame-level descriptors for each audio file
            descriptors_list = []
            paths = []
            n_missing = 0
            for rel_path in mp3_list:
                abs_path = os.path.join(media_dir, rel_path)
                if not os.path.exists(abs_path):
                    print(f"[AUDIO BUILD] Warning: audio file not found: {abs_path}")
                    n_missing += 1
                    continue

                # Here we expect the CSV to be the "light" CSV (10x13 descriptors stored as JSON)
                # If you don't provide CSV, we extract directly from files but reduce to 10 frames
                desc = None
                # try to find csv in base_dir and read descriptors if present
                if os.path.exists(csv_path):
                    # attempt to parse descriptors from CSV file (we will re-open and search row)
                    try:
                        # It's expensive to reopen for each file; but CSV is expected to be small (light)
                        with open(csv_path, "r", encoding=csv_encoding, errors="ignore") as fh:
                            reader = csv.DictReader(fh, delimiter=",")
                            for row in reader:
                                mp3_field = row.get("mp3") or row.get("mp3_path") or row.get("audio") or row.get("file")
                                if mp3_field and mp3_field.strip() == rel_path:
                                    desc_field = row.get("descriptors") or row.get("descriptores") or row.get("mfcc_frames")
                                    if desc_field:
                                        try:
                                            arr = json.loads(desc_field)
                                            desc = np.array(arr, dtype=np.float32)
                                        except Exception:
                                            desc = None
                                    break
                    except Exception:
                        desc = None

                if desc is None:
                    # fallback: extract directly from audio and reduce to 10 frames
                    desc = extract_audio_features(abs_path, n_mfcc=10, n_frames=40)

                if desc is None or desc.shape[0] == 0:
                    print(f"[AUDIO BUILD] Could not extract descriptors for {abs_path}")
                    n_missing += 1
                    continue

                descriptors_list.append(desc)
                rel = os.path.relpath(abs_path, media_dir).replace("\\", "/")
                paths.append(rel)


            if not descriptors_list:
                return {"ok": False, "error": "No valid audio descriptors extracted. Check files and format."}

            # 2) Train codebook with descriptors_list (list of arrays (frames, dim))
            mm_codebook_audio = Codebook(k=k)
            mm_codebook_audio.train(descriptors_list)

            # 3) Compute TF histograms (no TF-IDF yet)
            print("[AUDIO BUILD] Computing TF histograms for each audio...")
            hist_tf = [mm_codebook_audio.compute_histogram(desc, use_tfidf=False) for desc in descriptors_list]

            # 4) If use_tfidf -> build idf and recompute TF-IDF histograms
            if use_tfidf:
                print("[AUDIO BUILD] Building IDF and recomputing TF-IDF histograms...")
                mm_codebook_audio.build_idf(hist_tf)
                hist_tfidf = [mm_codebook_audio.compute_histogram(desc, use_tfidf=True) for desc in descriptors_list]
            else:
                hist_tfidf = hist_tf

            # 13) L2 normalize histograms for cosine similarity
            hist_tfidf = [l2_normalize_vec(h) for h in hist_tfidf]

            # Save codebook
            os.makedirs(base_dir, exist_ok=True)
            codebook_path = os.path.join(base_dir, "codebook_audio.pkl")
            mm_codebook_audio.save(codebook_path)

            # Save in-memory lists for search
            audio_descriptors_list = descriptors_list
            audio_index_paths = paths
            audio_histograms = hist_tfidf

            # 6) Build inverted-index style KNNIndexAudio (for 'index' search method)
            print("[AUDIO BUILD] Building inverted index structure for audio search...")
            knn_index_audio = KNNIndexAudio()
            # It expects descriptors per audio in build_index, so pass descriptors_list & paths
            knn_index_audio.build_index(descriptors_list, paths, mm_codebook_audio)

            # Done
            return {
                "ok": True,
                "message": "Audio index built successfully",
                "stats": {
                    "num_files_found_in_media": len(mp3_list),
                    "indexed_files": len(paths),
                    "missing_files": n_missing,
                    "vocabulary_size": k,
                    "use_tfidf": use_tfidf
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    @app.post("/multimedia/audio/search")
    def search_audio(
        file: UploadFile = File(...),
        top_k: int = Form(13),
        index_name: str = Form("default"),
        method: str = Form("sequential")  # 'sequential' or 'index'
    ):
        """
        Search for similar audio using either:
         - 'sequential' : compute histogram for query, then scan audio_histograms with heap (cosine)
         - 'index'      : use KNNIndexAudio inverted index (requires codebook + knn_index_audio built)
        """
        global audio_descriptors_list, audio_index_paths, audio_histograms
        global mm_codebook_audio, knn_index_audio

        if not audio_descriptors_list or not audio_index_paths:
            return {"ok": False, "error": "No audio index loaded. Build the audio index first."}

        temp_path = os.path.join(DATA_DIR, f"temp_audio_query_{file.filename}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # Extract frame-level descriptors for the query audio (10x13)
            query_descriptors = extract_audio_features(temp_path)
            os.remove(temp_path)
            if query_descriptors is None or query_descriptors.shape[0] == 0:
                return {"ok": False, "error": "Could not extract descriptors from query audio."}

            # Ensure codebook loaded
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")
            if mm_codebook_audio is None:
                codebook_path = os.path.join(base_dir, "codebook_audio.pkl")
                if not os.path.exists(codebook_path):
                    return {"ok": False, "error": "Audio codebook not found. Build the audio index first."}
                mm_codebook_audio = Codebook()
                mm_codebook_audio.load(codebook_path)

            if method == "sequential":
                # Query histogram (TF-IDF if codebook has idf)
                use_tfidf = mm_codebook_audio.idf is not None
                query_hist = mm_codebook_audio.compute_histogram(query_descriptors, use_tfidf=use_tfidf)
                query_hist = l2_normalize_vec(query_hist)

                # Heap for top-K (min-heap)
                heap = []
                for i, hist in enumerate(audio_histograms):
                    # both hist and query_hist are L2 normalized -> dot = cosine
                    sim = float(np.dot(query_hist, hist))
                    if len(heap) < top_k:
                        heapq.heappush(heap, (sim, audio_index_paths[i]))
                    else:
                        if sim > heap[0][0]:
                            heapq.heapreplace(heap, (sim, audio_index_paths[i]))

                # sort descending
                results = sorted(heap, key=lambda x: x[0], reverse=True)
                formatted_results = [
                    {"rank": i + 1, "filename": path, "similarity": float(sim)}
                    for i, (sim, path) in enumerate(results)
                ]

            elif method == "index":
                # Use inverted-index KNNIndexAudio
                if knn_index_audio is None:
                    knn_index_audio = KNNIndexAudio()
                    # we already built it in build_audio_index normally; if not, build from current data
                    knn_index_audio.build_index(audio_descriptors_list, audio_index_paths, mm_codebook_audio)

                # KNNIndexAudio.search expects descriptors (it will compute histogram internally)
                results = knn_index_audio.search(query_descriptors, mm_codebook_audio, top_k=top_k)
                # results format from your earlier implementation: list of (score, path)
                formatted_results = [
                    {"rank": i + 1, "filename": path, "similarity": float(sim)}
                    for i, (sim, path) in enumerate(results)
                ]
            else:
                return {"ok": False, "error": "Invalid search method. Choose 'sequential' or 'index'."}

            return {
                "ok": True,
                "results": formatted_results,
                "query_audio": {"filename": file.filename},
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
