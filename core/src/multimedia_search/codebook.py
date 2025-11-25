"""
Codebook Generation Module (Bag of Words)
Handles K-Means clustering to create visual/acoustic vocabularies.
"""

import numpy as np
import pickle
import os
import math
from sklearn.cluster import MiniBatchKMeans
from typing import List, Tuple, Dict
from collections import defaultdict

class Codebook:
    """
    Manages the visual/acoustic vocabulary using K-Means clustering.
    """
    
    def __init__(self, k: int = 100):
        """
        Args:
            k: Number of clusters (vocabulary size)
        """
        self.k = k
        self.kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=1000)
        self.is_trained = False
        
        # For TF-IDF calculation
        self.idf = None  # Inverse document frequency for each visual word
        self.num_docs = 0  # Total number of documents indexed
        
    def train(self, descriptors_list: List[np.ndarray]):
        """
        Train the codebook using a list of descriptor arrays.
        
        Args:
            descriptors_list: List of numpy arrays, where each array contains 
                            descriptors for one image/audio.
        """
        # Stack all descriptors vertically
        if not descriptors_list:
            print("No descriptors provided for training")
            return
            
        all_descriptors = np.vstack(descriptors_list)
        print(f"Training codebook with {all_descriptors.shape[0]} descriptors...")
        
        self.kmeans.fit(all_descriptors)
        self.is_trained = True
        print(f"Codebook trained with {self.k} clusters")
        
    def compute_histogram(self, descriptors: np.ndarray, use_tfidf: bool = False) -> np.ndarray:
        """
        Compute the Bag of Words histogram for a set of descriptors.
        
        Args:
            descriptors: Numpy array of descriptors (n_features, dim)
            use_tfidf: If True, apply TF-IDF weighting
            
        Returns:
            Histogram vector of size (k,)
        """
        if not self.is_trained:
            raise RuntimeError("Codebook not trained yet")
            
        if descriptors is None or len(descriptors) == 0:
            return np.zeros(self.k, dtype=np.float32)
            
        # Predict nearest cluster for each descriptor
        labels = self.kmeans.predict(descriptors)
        
        # Compute histogram (term frequency)
        hist, _ = np.histogram(labels, bins=range(self.k + 1))
        hist = hist.astype(np.float32)
        
        if use_tfidf and self.idf is not None:
            # Apply TF-IDF weighting
            # TF: log(1 + freq)
            tf = np.log1p(hist)
            # TF-IDF
            hist = tf * self.idf
            
        # Normalize histogram (L1 norm - sum to 1)
        # This makes it a probability distribution, ideal for Chi-Square distance
        norm = np.sum(hist)
        if norm > 0:
            hist = hist / norm
            
        return hist
    
    def build_idf(self, all_histograms: List[np.ndarray]):
        """
        Build IDF weights from a collection of histograms.
        
        Args:
            all_histograms: List of histogram vectors
        """
        self.num_docs = len(all_histograms)
        if self.num_docs == 0:
            return
            
        # Count document frequency for each visual word
        df = np.zeros(self.k)
        for hist in all_histograms:
            # A word appears in a document if its count > 0
            df += (hist > 0).astype(float)
            
        # Calculate IDF: log(N / df)
        # Add smoothing to avoid division by zero
        self.idf = np.log((self.num_docs + 1) / (df + 1))
        print(f"IDF built for {self.num_docs} documents")
        
    def save(self, path: str):
        """Save the trained codebook to disk."""
        data = {
            'kmeans': self.kmeans,
            'idf': self.idf,
            'num_docs': self.num_docs
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        print(f"Codebook saved to {path}")
            
    def load(self, path: str):
        """Load a trained codebook from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Codebook file not found: {path}")
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        # Handle both old and new format
        if isinstance(data, dict):
            self.kmeans = data['kmeans']
            self.idf = data.get('idf')
            self.num_docs = data.get('num_docs', 0)
        else:
            # Old format: just kmeans
            self.kmeans = data
            self.idf = None
            self.num_docs = 0
            
        self.is_trained = True
        self.k = self.kmeans.n_clusters
        print(f"Codebook loaded from {path}")
