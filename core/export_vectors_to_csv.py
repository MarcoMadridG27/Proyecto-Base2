import os
import csv
import pickle
import numpy as np
import argparse
import sys

# Add src to path to import KNNIndex if needed, though we might just load pickle directly
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def export_to_csv(index_name, output_file):
    base_dir = os.path.join("data", f"mm_index_{index_name}")
    index_path = os.path.join(base_dir, "index.pkl")
    
    if not os.path.exists(index_path):
        print(f"Error: Index file not found at {index_path}")
        return

    print(f"Loading index from {index_path}...")
    with open(index_path, 'rb') as f:
        data = pickle.load(f)
    
    vectors = data["vectors"]
    metadata = data["metadata"]
    
    print(f"Found {len(vectors)} vectors. Exporting to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Header
        writer.writerow(['id', 'path', 'vector'])
        
        for doc_id, vector in vectors.items():
            path = metadata.get(doc_id, "")
            
            # Format vector as string "[v1, v2, ...]"
            # Ensure it's a flat list
            if isinstance(vector, np.ndarray):
                vec_list = vector.flatten().tolist()
            else:
                vec_list = list(vector)
                
            vector_str = str(vec_list)
            
            writer.writerow([doc_id, path, vector_str])
            
    print(f"Export complete. Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export KNN Index vectors to CSV")
    parser.add_argument("--index_name", default="imagenes", help="Name of the index (e.g., 'imagenes')")
    parser.add_argument("--output", default="vectors_export.csv", help="Output CSV file path")
    
    args = parser.parse_args()
    
    export_to_csv(args.index_name, args.output)
