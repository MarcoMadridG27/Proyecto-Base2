"""
Query Processor - Handles text search queries using cosine similarity
Optimized for disk-based index access.
"""

import math
import heapq
from typing import List, Tuple, Dict
from collections import defaultdict
from .preprocessor import TextPreprocessor
from .spimi_indexer import SPIMIIndexer


class QueryProcessor:
    """
    Processes search queries and returns ranked results using cosine similarity.
    """
    
    def __init__(self, indexer: SPIMIIndexer):
        """
        Initialize query processor.
        
        Args:
            indexer: SPIMI indexer with built index
        """
        self.indexer = indexer
        self.preprocessor = TextPreprocessor(language='english', use_stemming=True)
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for documents matching the query.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of (doc_id, score) tuples, sorted by score descending
        """
        # Preprocess query
        query_terms = self.preprocessor.preprocess(query)
        
        if not query_terms:
            return []
        
        # Count term frequencies in query
        query_term_freqs = defaultdict(int)
        for term in query_terms:
            query_term_freqs[term] += 1
            
        # Accumulate scores: doc_id -> dot_product
        doc_scores = defaultdict(float)
        
        # Total documents for IDF
        N = self.indexer.num_docs
        if N == 0:
            return []
            
        # Process each unique query term
        query_norm_sq = 0.0
        
        for term, query_tf in query_term_freqs.items():
            # Retrieve postings from disk
            # Postings format: [(doc_id, tfidf_score), ...]
            postings = self.indexer.get_postings(term)
            
            if not postings:
                continue
                
            # Calculate Query TF-IDF
            # DF is the length of the postings list
            df = len(postings)
            idf = math.log(N / df) if df > 0 else 0
            
            # Query weight: (1 + log(tf)) * idf
            query_tf_weight = 1 + math.log(query_tf)
            query_weight = query_tf_weight * idf
            
            # Accumulate query norm squared
            query_norm_sq += query_weight ** 2
            
            # Accumulate dot product for each document
            for doc_id, doc_weight in postings:
                doc_scores[doc_id] += query_weight * doc_weight
        
        query_norm = math.sqrt(query_norm_sq)
        
        # Finalize scores with cosine normalization
        final_results = []
        
        for doc_id, dot_product in doc_scores.items():
            # Get document norm from metadata
            doc_norm = 0.0
            if doc_id in self.indexer.doc_metadata:
                doc_norm = self.indexer.doc_metadata[doc_id].get('norm', 0.0)
            
            if doc_norm > 0 and query_norm > 0:
                # Cosine Similarity = DotProduct / (QueryNorm * DocNorm)
                score = dot_product / (query_norm * doc_norm)
            else:
                score = 0.0
                
            final_results.append((doc_id, score))
            
        # Sort by score descending
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results[:top_k]
