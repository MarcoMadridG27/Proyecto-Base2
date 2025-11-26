"""
SPIMI - Single-Pass In-Memory Indexing
Constructs an inverted index efficiently using block-based approach
"""

import os
import json
import math
import pickle
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from .preprocessor import TextPreprocessor


class SPIMIIndexer:
    """
    SPIMI Indexer for building inverted index.
    
    Algorithm:
    1. Process documents in batches (blocks)
    2. Build partial inverted index for each block
    3. Write blocks to disk when memory limit reached
    4. Merge all blocks into final index
    5. Calculate TF-IDF weights
    """
    
    def __init__(self, index_dir: str = "data/text_index", block_size: int = 1000):
        """
        Initialize SPIMI indexer.
        
        Args:
            index_dir: Directory to store index files
            block_size: Number of documents per block
        """
        self.index_dir = index_dir
        self.block_size = block_size
        self.preprocessor = TextPreprocessor(language='english', use_stemming=True)
        
        # Create index directory
        os.makedirs(index_dir, exist_ok=True)
        
        # Inverted index: term -> [(doc_id, term_frequency), ...]
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        
        # Document metadata: doc_id -> {length, norm, ...}
        self.doc_metadata: Dict[int, Dict] = {}
        
        # Statistics
        self.num_docs = 0
        self.avg_doc_length = 0
        self.vocabulary: Set[str] = set()
        
    def build_block(self, documents: List[Tuple[int, str, Dict]]) -> Dict[str, Dict[int, int]]:
        """
        Build a partial inverted index for a block of documents.
        
        Args:
            documents: List of (doc_id, text, metadata) tuples
            
        Returns:
            Partial index: term -> {doc_id: term_frequency}
        """
        block_index = defaultdict(lambda: defaultdict(int))
        
        for doc_id, text, metadata in documents:
            # Preprocess text
            tokens = self.preprocessor.preprocess(text)
            
            # Count term frequencies
            for term in tokens:
                block_index[term][doc_id] += 1
            
            # Store document metadata
            self.doc_metadata[doc_id] = {
                'length': len(tokens),
                'unique_terms': len(set(tokens)),
                'text': text,  # Store original text for display
                **metadata     # Merge provided metadata
            }
        
        return block_index
    
    def write_block_to_disk(self, block_index: Dict, block_num: int):
        """
        Write a block index to disk.
        """
        block_path = os.path.join(self.index_dir, f"block_{block_num}.pkl")
        with open(block_path, 'wb') as f:
            pickle.dump(dict(block_index), f)
    
    def merge_blocks(self, num_blocks: int):
        """
        Merge all block indexes into final inverted index.
        """
        print(f"Merging {num_blocks} blocks...")
        
        for block_num in range(num_blocks):
            block_path = os.path.join(self.index_dir, f"block_{block_num}.pkl")
            
            with open(block_path, 'rb') as f:
                block_index = pickle.load(f)
            
            # Merge into main index
            for term, postings in block_index.items():
                self.vocabulary.add(term)
                for doc_id, tf in postings.items():
                    self.inverted_index[term].append((doc_id, tf))
            
            # Clean up block file
            os.remove(block_path)
        
        # Sort postings by doc_id for each term
        for term in self.inverted_index:
            self.inverted_index[term].sort(key=lambda x: x[0])
    
    def calculate_tf_idf(self):
        """
        Calculate TF-IDF weights and document norms.
        
        TF-IDF = (1 + log(tf)) * log(N / df)
        where:
        - tf = term frequency in document
        - df = document frequency (number of docs containing term)
        - N = total number of documents
        """
        print("Calculating TF-IDF weights...")
        
        N = self.num_docs
        
        # Calculate IDF for each term
        idf = {}
        for term, postings in self.inverted_index.items():
            df = len(postings)  # document frequency
            idf[term] = math.log(N / df) if df > 0 else 0
        
        # Calculate TF-IDF for each term-document pair
        tfidf_index = defaultdict(list)
        
        for term, postings in self.inverted_index.items():
            for doc_id, tf in postings:
                # TF-IDF weight
                tf_weight = 1 + math.log(tf) if tf > 0 else 0
                tfidf_weight = tf_weight * idf[term]
                tfidf_index[term].append((doc_id, tfidf_weight))
        
        # Replace raw TF with TF-IDF
        self.inverted_index = dict(tfidf_index)
        
        # Calculate document norms (for cosine similarity)
        doc_norms = defaultdict(float)
        for term, postings in self.inverted_index.items():
            for doc_id, tfidf in postings:
                doc_norms[doc_id] += tfidf ** 2
        
        # Store norms in metadata
        for doc_id, norm_squared in doc_norms.items():
            if doc_id in self.doc_metadata:
                self.doc_metadata[doc_id]['norm'] = math.sqrt(norm_squared)
    
    def build_index(self, documents: List[Tuple[int, str, Dict]]):
        """
        Build complete inverted index from documents using SPIMI.
        
        Args:
            documents: List of (doc_id, text, metadata) tuples
        """
        print(f"Building index for {len(documents)} documents...")
        
        self.num_docs = len(documents)
        num_blocks = 0
        
        # Process documents in blocks
        for i in range(0, len(documents), self.block_size):
            block_docs = documents[i:i + self.block_size]
            
            print(f"Processing block {num_blocks + 1} ({len(block_docs)} docs)...")
            
            # Build block index
            block_index = self.build_block(block_docs)
            
            # Write to disk
            self.write_block_to_disk(block_index, num_blocks)
            
            num_blocks += 1
        
        # Merge all blocks
        self.merge_blocks(num_blocks)
        
        # Calculate TF-IDF
        self.calculate_tf_idf()
        
        # Calculate average document length
        total_length = sum(meta['length'] for meta in self.doc_metadata.values())
        self.avg_doc_length = total_length / self.num_docs if self.num_docs > 0 else 0
        
        print(f"Index built successfully!")
        print(f"  - Vocabulary size: {len(self.vocabulary)}")
        print(f"  - Total documents: {self.num_docs}")
        print(f"  - Average doc length: {self.avg_doc_length:.2f}")
    
    def save_index(self):
        """
        Save the complete index to disk.
        """
        index_path = os.path.join(self.index_dir, "inverted_index.pkl")
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        
        # Save inverted index
        with open(index_path, 'wb') as f:
            pickle.dump(dict(self.inverted_index), f)
        
        # Save metadata
        metadata = {
            'num_docs': self.num_docs,
            'avg_doc_length': self.avg_doc_length,
            'vocabulary_size': len(self.vocabulary),
            'doc_metadata': self.doc_metadata
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Index saved to {self.index_dir}")
    
    def load_index(self):
        """
        Load index from disk.
        """
        index_path = os.path.join(self.index_dir, "inverted_index.pkl")
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError("Index files not found. Build index first.")
        
        # Load inverted index
        with open(index_path, 'rb') as f:
            self.inverted_index = pickle.load(f)
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.num_docs = metadata['num_docs']
        self.avg_doc_length = metadata['avg_doc_length']
        self.doc_metadata = {int(k): v for k, v in metadata['doc_metadata'].items()}
        self.vocabulary = set(self.inverted_index.keys())
        
        print(f"Index loaded from {self.index_dir}")
        print(f"  - Vocabulary size: {len(self.vocabulary)}")
        print(f"  - Total documents: {self.num_docs}")


# Example usage
if __name__ == "__main__":
    # Sample documents
    documents = [
        (1, "The quick brown fox jumps over the lazy dog"),
        (2, "A quick brown dog outpaces a quick fox"),
        (3, "The lazy cat sleeps all day long"),
        (4, "Dogs and cats are popular pets"),
        (5, "The fox is a clever animal")
    ]
    
    # Build index
    indexer = SPIMIIndexer(index_dir="data/test_index", block_size=2)
    indexer.build_index(documents)
    indexer.save_index()
    
    # Print index
    print("\nInverted Index (TF-IDF):")
    for term in sorted(indexer.inverted_index.keys())[:10]:
        print(f"{term}: {indexer.inverted_index[term]}")
