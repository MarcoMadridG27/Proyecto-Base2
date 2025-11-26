"""
KNN Index for Multimedia Similarity Search
Handles storage and retrieval of feature vectors (histograms).
"""

import numpy as np
import pickle
import os
import heapq
from typing import List, Tuple, Dict

class KNNIndex:
    """
    Manages feature vectors and performs KNN search.
    """
    
    def __init__(self, index_dir: str = "data/multimedia_index"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        
        # Dictionary to store vectors: doc_id -> vector
        self.vectors: Dict[int, np.ndarray] = {}
        # Metadata: doc_id -> file_path
        self.metadata: Dict[int, str] = {}
        
    def add_vector(self, doc_id: int, vector: np.ndarray, file_path: str):
        """Add a vector to the index."""
        self.vectors[doc_id] = vector
        self.metadata[doc_id] = file_path
        
    def search_sequential(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[float, int, str]]:
        """
        Perform sequential KNN search using Chi-Square distance.
        Chi-Square is significantly better for histogram comparison than Euclidean.
        
        Returns:
            List of (distance, doc_id, file_path) sorted by distance (ascending).
        """
        heap = []
        eps = 1e-10  # Small epsilon to avoid division by zero
        
        for doc_id, vector in self.vectors.items():
            # Chi-Square distance
            # d(x,y) = 0.5 * sum((xi-yi)^2 / (xi+yi+eps))
            numerator = (query_vector - vector) ** 2
            denominator = query_vector + vector + eps
            
            # Avoid division by zero where denominator is very small
            # This can happen if both vectors have 0 at the same index
            valid_mask = denominator > eps
            
            dist = 0.0
            if np.any(valid_mask):
                dist = 0.5 * np.sum(numerator[valid_mask] / denominator[valid_mask])
            
            # Maintain top-k smallest distances using a max-heap of size k
            # We store (-dist, ...) because heapq is a min-heap
            if len(heap) < k:
                heapq.heappush(heap, (-dist, doc_id, self.metadata[doc_id]))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, doc_id, self.metadata[doc_id]))
                
        # Convert back to positive distances and sort
        results = [(-d, doc_id, path) for d, doc_id, path in heap]
        results.sort(key=lambda x: x[0])
        
        return results
        
    def save(self, name: str = "index"):
        """Save index to disk."""
        path = os.path.join(self.index_dir, f"{name}.pkl")
        data = {
            "vectors": self.vectors,
            "metadata": self.metadata
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        print(f"Index saved to {path}")
        
    def load(self, name: str = "index"):
        """Load index from disk."""
        path = os.path.join(self.index_dir, f"{name}.pkl")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        self.vectors = data["vectors"]
        self.metadata = data["metadata"]
        print(f"Index loaded from {path} with {len(self.vectors)} items")
