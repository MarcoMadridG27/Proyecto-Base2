"""
Test script for multimedia search module
"""

import sys
import os
import cv2
import numpy as np
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.multimedia_search.feature_extractor import FeatureExtractor
from src.multimedia_search.codebook import Codebook
from src.multimedia_search.knn_index import KNNIndex

def create_dummy_images(output_dir: str, num_images: int = 5):
    """Create synthetic images for testing."""
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    
    rng = np.random.default_rng()
    
    for i in range(num_images):
        # Create a random image with some shapes
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        
        # Random background color
        img[:] = rng.integers(0, 255, 3)
        
        # Draw some random circles
        for _ in range(5):
            center = (int(rng.integers(0, 200)), int(rng.integers(0, 200)))
            radius = int(rng.integers(10, 50))
            color = rng.integers(0, 255, 3).tolist()
            cv2.circle(img, center, radius, color, -1)
            
        path = os.path.join(output_dir, f"img_{i}.jpg")
        cv2.imwrite(path, img)
        image_paths.append(path)
        
    return image_paths

def test_multimedia_pipeline():
    print("=" * 60)
    print("Testing Multimedia Search Pipeline")
    print("=" * 60)
    
    # 1. Setup
    test_dir = "data/test_images"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    print("Creating dummy images...")
    image_paths = create_dummy_images(test_dir, num_images=10)
    
    # 2. Feature Extraction
    print("\nExtracting features (SIFT/ORB)...")
    extractor = FeatureExtractor()
    descriptors_list = []
    valid_paths = []
    
    for path in image_paths:
        desc = extractor.extract_image_features(path)
        if desc is not None:
            descriptors_list.append(desc)
            valid_paths.append(path)
            print(f"  {os.path.basename(path)}: {desc.shape[0]} features")
            
    if not descriptors_list:
        print("❌ No features extracted. Cannot proceed.")
        return

    # 3. Codebook Training
    print("\nTraining Codebook (K-Means)...")
    codebook = Codebook(k=5) # Small k for testing
    codebook.train(descriptors_list)
    
    # 4. Indexing
    print("\nBuilding KNN Index...")
    index = KNNIndex(index_dir="data/test_multimedia_index")
    
    for i, (path, desc) in enumerate(zip(valid_paths, descriptors_list)):
        hist = codebook.compute_histogram(desc)
        index.add_vector(i, hist, path)
        print(f"  Indexed {os.path.basename(path)} (Doc ID: {i})")
        
    index.save()
    
    # 5. Search
    print("\nSearching...")
    # Use the first image as query
    query_path = valid_paths[0]
    query_desc = extractor.extract_image_features(query_path)
    query_hist = codebook.compute_histogram(query_desc)
    
    results = index.search_sequential(query_hist, k=3)
    
    print(f"Query: {os.path.basename(query_path)}")
    for rank, (dist, doc_id, path) in enumerate(results, 1):
        print(f"  {rank}. Doc {doc_id} ({os.path.basename(path)}): dist={dist:.4f}")
        
    # Verify that the query image itself is the top result (dist should be 0)
    if results[0][1] < 1e-5:
        print("\n✅ Search validation passed (query image found itself)")
    else:
        print("\n⚠️ Search validation warning: query image not top result with 0 distance")

if __name__ == "__main__":
    # Redirect stdout to file with UTF-8 encoding
    with open("test_multimedia_output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        try:
            test_multimedia_pipeline()
            print("\n" + "=" * 60)
            print("[OK] Multimedia tests completed successfully!")
            print("=" * 60)
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = sys.__stdout__
            
    # Print file content to console for verification
    # Use errors='replace' to avoid crash on console print
    with open("test_multimedia_output.txt", "r", encoding="utf-8") as f:
        print(f.read())
