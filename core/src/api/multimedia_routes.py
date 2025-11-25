"""
Multimedia Search Endpoints for FastAPI
"""

from fastapi import UploadFile, File, Form
from typing import Optional
import os
import shutil
import time
import zipfile

from src.multimedia_search.feature_extractor import FeatureExtractor
from src.multimedia_search.codebook import Codebook
from src.multimedia_search.knn_index import KNNIndex
from src.multimedia_search.visual_inverted_index import VisualInvertedIndex

# Global multimedia instances
mm_extractor = FeatureExtractor()
mm_codebook: Optional[Codebook] = None
mm_index: Optional[KNNIndex] = None
mm_inverted_index: Optional[VisualInvertedIndex] = None


def register_multimedia_routes(app, DATA_DIR):
    """Register multimedia search endpoints to the FastAPI app"""
    
    # Mount static files for serving images
    from fastapi.staticfiles import StaticFiles
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
    
    @app.post("/multimedia/build_index")
    async def build_multimedia_index(
        file: UploadFile = File(...),
        k: int = Form(100),
        index_name: str = Form("default"),
        use_tfidf: bool = Form(True)
    ):
        """
        Build multimedia index from a ZIP file containing images.
        1. Extract ZIP
        2. Extract features (SIFT/ORB)
        3. Train Codebook (K-Means)
        4. Build TF-IDF weights
        5. Build KNN Index (sequential)
        6. Build Inverted Index (indexed)
        """
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
            for path in media_files:
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
                    desc = mm_extractor.extract_image_features(path)
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
    async def search_multimedia(
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
            results = mm_index.search_sequential(hist, k=top_k)
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
    async def compare_search_methods(
        file: UploadFile = File(...),
        top_k: int = Form(5),
        index_name: str = Form("default")
    ):
        """
        Compare sequential vs indexed search methods.
        Returns timing and results for both approaches.
        """
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
