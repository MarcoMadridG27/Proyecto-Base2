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
import numpy as np
import librosa
from typing import Optional

from src.multimedia_search.feature_extractor import FeatureExtractor
from src.multimedia_search.codebook import Codebook
from src.multimedia_search.knn_index import KNNIndex
from src.multimedia_search.visual_inverted_index import VisualInvertedIndex

# Global multimedia instances
mm_extractor = FeatureExtractor()
mm_codebook: Optional[Codebook] = None
mm_index: Optional[KNNIndex] = None
mm_inverted_index: Optional[VisualInvertedIndex] = None

# Add audio-specific globals
mm_codebook_audio: Optional[Codebook] = None
mm_index_audio: Optional[KNNIndex] = None
mm_inverted_index_audio: Optional[VisualInvertedIndex] = None

# Almacena los MFCCs originales en memoria para búsqueda exhaustiva
audio_index_vectors = []
audio_index_paths = []

def extract_audio_features(filepath, n_mfcc=50):
    y, sr = librosa.load(filepath, sr=None)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    mfcc_mean = np.mean(mfcc, axis=1).astype(np.float32)
    return mfcc_mean  # shape: (n_mfcc,)

def _parse_vector_string(s: str):
    """Robust parser for vectors like '[1.23 4.56 -7.8]' or '[1.0,2.0,...]'"""
    # Limpia saltos de línea y espacios extra
    s = s.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ').strip()
    # Elimina comillas si existen
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # Busca números with regex
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
                return {"ok": False, "error": "No images found in ZIP"}
                
            # 1. Extract Features
            start_time = time.time()
            print(f"Extracting features from {len(media_files)} files...")
            
            # Detect file types and extract features
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
            
            descriptors_list = []
            total_files = len(media_files)
            for i, path in enumerate(media_files):
                if i % 100 == 0:
                    print(f"Processing file {i+1}/{total_files}: {os.path.basename(path)}")
                    
                if path.lower().endswith(image_extensions):
                    desc = mm_extractor.extract_image_features(path)
                elif path.lower().endswith(audio_extensions):
                    desc = mm_extractor.extract_audio_features(path)
                else:
                    continue
                    
                if desc is not None:
                    descriptors_list.append(desc)
            
            if not descriptors_list:
                return {"ok": False, "error": "Could not extract features from any file"}
                
            # 2. Train Codebook
            print(f"Training codebook with k={k}...")
            mm_codebook = Codebook(k=k)
            mm_codebook.train(descriptors_list)
            
            # 3. Compute histograms for all files (without TF-IDF first)
            print("Computing histograms...")
            all_histograms = []
            valid_paths = []
            for path in media_files:
                # Detect file type and extract features
                if path.lower().endswith(image_extensions):
                    desc = mm_extractor.extract_image_features(path)
                elif path.lower().endswith(audio_extensions):
                    desc = mm_extractor.extract_audio_features(path)
                else:
                    continue
                    
                if desc is not None:
                    hist = mm_codebook.compute_histogram(desc, use_tfidf=False)
                    all_histograms.append(hist)
                    valid_paths.append(path)
            
            # 4. Build IDF if using TF-IDF
            if use_tfidf:
                print("Building IDF weights...")
                mm_codebook.build_idf(all_histograms)
                
                # Recompute histograms with TF-IDF
                all_histograms = []
                for path in valid_paths:
                    # Detect file type and extract features
                    if path.lower().endswith(image_extensions):
                        desc = mm_extractor.extract_image_features(path)
                    elif path.lower().endswith(audio_extensions):
                        desc = mm_extractor.extract_audio_features(path)
                    else:
                        continue
                        
                    if desc is not None:
                        hist = mm_codebook.compute_histogram(desc, use_tfidf=True)
                        all_histograms.append(hist)
            
            # Save codebook
            mm_codebook.save(os.path.join(base_dir, "codebook.pkl"))
            
            # 5. Build KNN Sequential Index
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
        top_k: int = Form(5),
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
                desc = mm_extractor.extract_audio_features(temp_path)
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
                # Chi-Square distance is roughly between 0 and 1 for L1 normalized histograms
                # We clamp it to ensure it's valid
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
        top_k: int = Form(5),
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
                desc = mm_extractor.extract_audio_features(temp_path)
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
        k: int = Form(50),
        index_name: str = Form("default"),
        use_tfidf: bool = Form(True),
        csv_encoding: str = Form("utf-8"),
        use_server_csv: bool = Form(False),
    ):
        global audio_index_vectors, audio_index_paths

        try:
            base_dir = os.path.join(DATA_DIR, f"mm_index_{index_name}")
            media_dir = os.path.join(base_dir, "media")
            os.makedirs(media_dir, exist_ok=True)

            csv_path = os.path.join(base_dir, "audio_dataset.csv")

            # If file uploaded -> save; else if use_server_csv -> expect csv already at csv_path
            if file is not None:
                print(f"[AUDIO BUILD] Uploading CSV file...")
                with open(csv_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            else:
                if not (use_server_csv and os.path.exists(csv_path)):
                    return {
                        "ok": False,
                        "error": f"No CSV uploaded and no server CSV found at {csv_path}. Either upload a CSV or place audio_dataset.csv in the index directory."
                    }
                print(f"[AUDIO BUILD] Using server CSV from: {csv_path}")

            # Detect delimiter and open CSV safely
            print(f"[AUDIO BUILD] Parsing CSV from: {csv_path}")
            with open(csv_path, "r", encoding=csv_encoding, errors="ignore") as fh:
                reader = csv.DictReader(fh, delimiter=",")
                audio_index_vectors = []
                audio_index_paths = []
                for row_idx, row in enumerate(reader):
                    # Admite columnas con nombres diferentes y vector en formato CSV
                    vector_field = None
                    for key in row.keys():
                        if key.strip().lower() in ["mfcc_vector", "mfcc", "mfccvector"]:
                            vector_field = row[key]
                            break
                    mp3_field = row.get("mp3") or row.get("mp3_path") or row.get("audio") or row.get("file")
                    if vector_field is None or not vector_field.strip():
                        continue
                    # Si el vector está entre comillas y separado por comas, lo parsea igual
                    arr = _parse_vector_string(vector_field)
                    if arr is None:
                        continue
                    mfcc_vec = arr.flatten().astype(np.float32)
                    audio_index_vectors.append(mfcc_vec)
                    audio_index_paths.append(mp3_field or f"track_{row_idx}")
            
            return {
                "ok": True,
                "message": "Audio index built from CSV",
                "stats": {
                    "num_records": len(audio_index_vectors),
                    "indexed_files": len(audio_index_paths),
                    "vocabulary_size": k
                }
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

    @app.post("/multimedia/audio/search")
    def search_audio(
        file: UploadFile = File(...),
        top_k: int = Form(5),
        index_name: str = Form("default")
    ):
        import librosa
        global audio_index_vectors, audio_index_paths

        if not audio_index_vectors or not audio_index_paths:
            return {"ok": False, "error": "No index loaded. Build the audio index first."}

        temp_path = os.path.join(DATA_DIR, f"temp_audio_query_{file.filename}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            duration = librosa.get_duration(path=temp_path)
        except Exception:
            duration = None

        query_vec = extract_audio_features(temp_path, n_mfcc=50)
        os.remove(temp_path)
        if query_vec is None:
            return {"ok": False, "error": "Could not extract features from query audio."}

        # --- Medir tiempo de búsqueda ---
        start_time = time.time()
        dists = []
        for idx, vec in enumerate(audio_index_vectors):
            dist = np.linalg.norm(query_vec - vec)
            dists.append((dist, idx))
        dists.sort(key=lambda x: x[0])
        results = []
        for rank, (dist, idx) in enumerate(dists[:top_k], 1):
            similarity = max(0.0, 1.0 - dist / (np.linalg.norm(query_vec) + 1e-8))
            result_path = os.path.join(DATA_DIR, "mm_index_" + index_name, "media", audio_index_paths[idx])
            try:
                result_duration = librosa.get_duration(path=result_path)
            except Exception:
                result_duration = None
            results.append({
                "rank": rank,
                "filename": audio_index_paths[idx],
                "distance": float(dist),
                "similarity": similarity,
                "duration": result_duration
            })
        end_time = time.time()
        search_time_seconds = end_time - start_time
        # --- Fin medición ---

        return {
            "ok": True,
            "results": results,
            "query_audio": {
                "filename": file.filename,
                "duration": duration
            },
            "search_time_seconds": search_time_seconds
        }
