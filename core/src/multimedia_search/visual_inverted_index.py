"""
Inverted Index for Visual Words (KNN Indexado)
Implements an inverted index structure for efficient similarity search.
"""

import numpy as np
import pickle
import os
import heapq
from typing import List, Tuple, Dict
from collections import defaultdict

class VisualInvertedIndex:
    """
    Inverted index for visual words to enable efficient KNN search.
    Maps visual words to documents containing them.
    """
    
    def __init__(self, index_dir: str = "data/multimedia_index"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        
        # Inverted index: visual_word_id -> [(doc_id, tf_idf_weight), ...]
        self.inverted_index: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        
        # Document vectors (for normalization)
        self.doc_norms: Dict[int, float] = {}
        
        # Metadata
        self.metadata: Dict[int, str] = {}
        
    def add_document(self, doc_id: int, histogram: np.ndarray, file_path: str):
        """
        Add a document to the inverted index.
        
        Args:
            doc_id: Document ID
            histogram: TF-IDF weighted histogram vector
            file_path: Path to the original file
        """
        # Store metadata
        self.metadata[doc_id] = file_path
        
        # Calculate document norm
        norm = np.linalg.norm(histogram)
        self.doc_norms[doc_id] = norm
        
        # Add to inverted index (only non-zero entries)
        for visual_word_id, weight in enumerate(histogram):
            if weight > 0:
                self.inverted_index[visual_word_id].append((doc_id, weight))
                
    def search(self, query_histogram: np.ndarray, k: int = 5) -> List[Tuple[int, float, str]]:
        """
        Search for similar documents using the inverted index.
        
        Args:
            query_histogram: TF-IDF weighted query histogram
            k: Number of results to return
            
        Returns:
            List of (doc_id, similarity_score, file_path) sorted by similarity
        """
        # Calculate query norm
        query_norm = np.linalg.norm(query_histogram)
        if query_norm == 0:
            return []
            
        # Accumulate scores for candidate documents
        scores = defaultdict(float)
        
        # For each non-zero visual word in query
        for visual_word_id, query_weight in enumerate(query_histogram):
            if query_weight > 0 and visual_word_id in self.inverted_index:
                # Get all documents containing this visual word
                for doc_id, doc_weight in self.inverted_index[visual_word_id]:
                    # Accumulate dot product
                    scores[doc_id] += query_weight * doc_weight
                    
        # Calculate cosine similarity and get top-k
        heap = []
        for doc_id, dot_product in scores.items():
            doc_norm = self.doc_norms.get(doc_id, 1.0)
            similarity = dot_product / (query_norm * doc_norm)
            
            if len(heap) < k:
                heapq.heappush(heap, (similarity, doc_id))
            elif similarity > heap[0][0]:
                heapq.heapreplace(heap, (similarity, doc_id))
                
        # Sort results by similarity (descending)
        results = [(doc_id, sim, self.metadata.get(doc_id, "")) 
                   for sim, doc_id in sorted(heap, reverse=True)]
        
        return results
        
    def save(self, name: str = "inverted_index"):
        """Save index to disk."""
        path = os.path.join(self.index_dir, f"{name}.pkl")
        data = {
            "inverted_index": dict(self.inverted_index),
            "doc_norms": self.doc_norms,
            "metadata": self.metadata
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        print(f"Inverted index saved to {path}")
        
    def load(self, name: str = "inverted_index"):
        """Load index from disk."""
        path = os.path.join(self.index_dir, f"{name}.pkl")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        self.inverted_index = defaultdict(list, data["inverted_index"])
        self.doc_norms = data["doc_norms"]
        self.metadata = data["metadata"]
        print(f"Inverted index loaded from {path} with {len(self.metadata)} documents")
        
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "num_documents": len(self.metadata),
            "num_visual_words": len(self.inverted_index),
            "avg_postings_per_word": sum(len(postings) for postings in self.inverted_index.values()) / max(len(self.inverted_index), 1)
        }
