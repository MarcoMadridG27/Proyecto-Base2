"""
SPIMI - Single-Pass In-Memory Indexing
Constructs an inverted index efficiently using block-based approach
Optimized for secondary memory usage as per requirements.
"""

import os
import json
import math
import pickle
import heapq
from typing import Dict, List, Tuple, Set, Iterator
from collections import defaultdict
from .preprocessor import TextPreprocessor


class SPIMIIndexer:
    """
    SPIMI Indexer for building inverted index on disk.
    
    Algorithm:
    1. Process documents in batches (blocks)
    2. Build partial inverted index for each block in RAM
    3. Write blocks to disk as sorted text files
    4. Merge all blocks into final index (k-way merge)
    5. Calculate TF-IDF on the fly during merge
    6. Store final index on disk, keep only vocabulary in RAM
    """
    
    INDEX_FILENAME = "inverted_index.dat"

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
        
        # In-memory vocabulary: term -> file_offset
        self.vocabulary: Dict[str, int] = {}
        
        # Document metadata: doc_id -> {length, norm, ...}
        self.doc_metadata: Dict[int, Dict] = {}
        
        # Statistics
        self.num_docs = 0
        self.avg_doc_length = 0
        
        # File handle for reading index
        self.read_handle = None
        
    def build_block(self, documents: List[Tuple[int, str, Dict]]) -> Dict[str, Dict[int, int]]:
        """
        Build a partial inverted index for a block of documents.
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
        Write a block index to disk as a sorted text file.
        Format: term|json_postings
        """
        block_path = os.path.join(self.index_dir, f"block_{block_num}.txt")
        
        # Sort terms for merging
        sorted_terms = sorted(block_index.keys())
        
        with open(block_path, 'w', encoding='utf-8', newline='') as f:
            for term in sorted_terms:
                postings = block_index[term] # {doc_id: freq}
                # Save as list of tuples for compactness: [[doc_id, freq], ...]
                postings_list = list(postings.items())
                f.write(f"{term}|{json.dumps(postings_list)}\n")
    
    def _block_iterator(self, file_obj, block_idx) -> Iterator[Tuple[str, List, int]]:
        """Generator to read a block file line by line."""
        for line in file_obj:
            try:
                term, postings_json = line.strip().split('|', 1)
                postings = json.loads(postings_json)
                yield term, postings, block_idx
            except ValueError:
                continue

    def _write_term_to_index(self, term: str, postings: List[Tuple[int, int]], 
                           total_docs: int, doc_norms: Dict[int, float], index_file):
        """
        Calculate TF-IDF and write term to final index.
        """
        # Calculate IDF
        df = len(postings)
        idf = math.log(total_docs / df) if df > 0 else 0
        
        final_postings = []
        for doc_id, tf in postings:
            # TF-IDF weight: (1 + log(tf)) * log(N / df)
            tf_weight = 1 + math.log(tf) if tf > 0 else 0
            tfidf = tf_weight * idf
            
            # Keep significant precision but save space
            tfidf = round(tfidf, 4)
            
            final_postings.append((doc_id, tfidf))
            
            # Accumulate norm squared
            doc_norms[doc_id] += tfidf ** 2
            
        # Sort postings by doc_id
        final_postings.sort(key=lambda x: x[0])
        
        # Record offset in vocabulary
        offset = index_file.tell()
        self.vocabulary[term] = offset
        
        # Write to file: term|[(doc_id, score), ...]
        index_file.write(f"{term}|{json.dumps(final_postings)}\n")

    def merge_blocks(self, num_blocks: int):
        """
        Merge all block indexes into final inverted index using k-way merge.
        Calculates TF-IDF and document norms on the fly.
        """
        print(f"Merging {num_blocks} blocks...")
        
        # Open all block files
        files = []
        block_iters = []
        
        for i in range(num_blocks):
            try:
                f = open(os.path.join(self.index_dir, f"block_{i}.txt"), 'r', encoding='utf-8', newline='')
                files.append(f)
                block_iters.append(self._block_iterator(f, i))
            except FileNotFoundError:
                print(f"Warning: Block {i} not found")
                continue
            
        # Min-heap for k-way merge: (term, block_idx, postings)
        heap = []
        for i, iterator in enumerate(block_iters):
            try:
                term, postings, block_idx = next(iterator)
                # Use block_idx as tie-breaker for heap stability
                heapq.heappush(heap, (term, i, postings))
            except StopIteration:
                pass
                
        # Output file
        final_index_path = os.path.join(self.index_dir, self.INDEX_FILENAME)
        index_file = open(final_index_path, 'w', encoding='utf-8', newline='')
        
        current_term = None
        current_postings = []
        
        # For TF-IDF
        total_docs = self.num_docs
        doc_norms = defaultdict(float)
        
        count = 0
        while heap:
            term, block_idx, postings = heapq.heappop(heap)
            
            if current_term is None:
                current_term = term
            
            if term != current_term:
                # Process finished term
                self._write_term_to_index(current_term, current_postings, total_docs, doc_norms, index_file)
                current_term = term
                current_postings = []
                count += 1
                if count % 10000 == 0:
                    print(f"Merged {count} terms...")
                
            current_postings.extend(postings)
            
            # Fetch next from this block
            try:
                next_term, next_postings, _ = next(block_iters[block_idx])
                heapq.heappush(heap, (next_term, block_idx, next_postings))
            except StopIteration:
                pass
                
        # Process last term
        if current_term:
            self._write_term_to_index(current_term, current_postings, total_docs, doc_norms, index_file)
            
        # Close files
        index_file.close()
        for f in files:
            f.close()
            
        # Clean up block files
        for i in range(num_blocks):
            try:
                os.remove(os.path.join(self.index_dir, f"block_{i}.txt"))
            except OSError:
                pass
            
        # Update metadata with norms
        for doc_id, norm_sq in doc_norms.items():
            if doc_id in self.doc_metadata:
                self.doc_metadata[doc_id]['norm'] = math.sqrt(norm_sq)
                
        print(f"Merge complete. Vocabulary size: {len(self.vocabulary)}")
    
    def build_index(self, documents: List[Tuple[int, str, Dict]]):
        """
        Build complete inverted index from documents using SPIMI.
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
        
        # Calculate average document length
        total_length = sum(meta['length'] for meta in self.doc_metadata.values())
        self.avg_doc_length = total_length / self.num_docs if self.num_docs > 0 else 0
        
        # Save metadata and vocabulary
        self.save_index()
        
        print(f"Index built successfully!")
    
    def save_index(self):
        """
        Save metadata and vocabulary to disk.
        """
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        vocab_path = os.path.join(self.index_dir, "vocabulary.pkl")
        
        # Save metadata
        metadata = {
            'num_docs': self.num_docs,
            'avg_doc_length': self.avg_doc_length,
            'doc_metadata': self.doc_metadata
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        # Save vocabulary
        with open(vocab_path, 'wb') as f:
            pickle.dump(self.vocabulary, f)
            
        print(f"Index metadata saved to {self.index_dir}")
    
    def load_index(self):
        """
        Load index metadata and vocabulary from disk.
        Does NOT load the full inverted index.
        """
        metadata_path = os.path.join(self.index_dir, "metadata.json")
        vocab_path = os.path.join(self.index_dir, "vocabulary.pkl")
        index_path = os.path.join(self.index_dir, self.INDEX_FILENAME)
        
        if not os.path.exists(metadata_path) or not os.path.exists(vocab_path) or not os.path.exists(index_path):
            raise FileNotFoundError("Index files not found. Build index first.")
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.num_docs = metadata['num_docs']
        self.avg_doc_length = metadata['avg_doc_length']
        self.doc_metadata = {int(k): v for k, v in metadata['doc_metadata'].items()}
        
        # Load vocabulary
        with open(vocab_path, 'rb') as f:
            self.vocabulary = pickle.load(f)
            
        print(f"Index loaded from {self.index_dir}")
        print(f"  - Vocabulary size: {len(self.vocabulary)}")
        print(f"  - Total documents: {self.num_docs}")
        
        # Open read handle
        self.read_handle = open(index_path, 'r', encoding='utf-8', newline='')

    def get_postings(self, term: str) -> List[Tuple[int, float]]:
        """
        Retrieve postings list for a term from disk.
        
        Args:
            term: Search term
            
        Returns:
            List of (doc_id, tfidf_score)
        """
        if term not in self.vocabulary:
            return []
        
        offset = self.vocabulary[term]
        
        if self.read_handle is None or self.read_handle.closed:
            self.read_handle = open(os.path.join(self.index_dir, self.INDEX_FILENAME), 'r', encoding='utf-8', newline='')
            
        self.read_handle.seek(offset)
        line = self.read_handle.readline()
        
        print(f"DEBUG: term={term}, offset={offset}, line_len={len(line)}, line_start={line[:20] if line else 'EOF'}", flush=True)
        
        if not line:
            return []
            
        try:
            _, postings_json = line.strip().split('|', 1)
            return json.loads(postings_json)
        except ValueError:
            return []

    def close(self):
        """Close file handles."""
        if self.read_handle and not self.read_handle.closed:
            self.read_handle.close()
