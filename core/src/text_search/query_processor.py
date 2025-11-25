"""
Query Processor - Handles text search queries using cosine similarity
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
    
    def calculate_query_tfidf(self, query_terms: List[str]) -> Dict[str, float]:
        """
        Calculate TF-IDF weights for query terms.
        
        Args:
            query_terms: Preprocessed query terms
            
        Returns:
            Dictionary: term -> tfidf weight
        """
        # Count term frequencies in query
        term_freq = defaultdict(int)
        for term in query_terms:
            term_freq[term] += 1
        
        # Calculate TF-IDF for query
        query_tfidf = {}
        N = self.indexer.num_docs
        
        for term, tf in term_freq.items():
            if term in self.indexer.inverted_index:
                # Document frequency
                df = len(self.indexer.inverted_index[term])
                
                # IDF
                idf = math.log(N / df) if df > 0 else 0
                
                # TF weight (1 + log(tf))
                tf_weight = 1 + math.log(tf) if tf > 0 else 0
                
                # TF-IDF
                query_tfidf[term] = tf_weight * idf
        
        return query_tfidf
    
    def cosine_similarity(self, query_tfidf: Dict[str, float], doc_id: int) -> float:
        """
        Calculate cosine similarity between query and document.
        
        Cosine similarity = (query · doc) / (||query|| * ||doc||)
        
        Args:
            query_tfidf: Query TF-IDF weights
            doc_id: Document ID
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        # Get document norm
        if doc_id not in self.indexer.doc_metadata:
            return 0.0
        
        doc_norm = self.indexer.doc_metadata[doc_id].get('norm', 0)
        if doc_norm == 0:
            return 0.0
        
        # Calculate dot product
        dot_product = 0.0
        for term, query_weight in query_tfidf.items():
            if term in self.indexer.inverted_index:
                # Find document's weight for this term
                for doc, doc_weight in self.indexer.inverted_index[term]:
                    if doc == doc_id:
                        dot_product += query_weight * doc_weight
                        break
        
        # Calculate query norm
        query_norm = math.sqrt(sum(w ** 2 for w in query_tfidf.values()))
        
        if query_norm == 0:
            return 0.0
        
        # Cosine similarity
        similarity = dot_product / (query_norm * doc_norm)
        
        return similarity
    
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
        
        # Calculate query TF-IDF
        query_tfidf = self.calculate_query_tfidf(query_terms)
        
        if not query_tfidf:
            return []
        
        # Find candidate documents (documents containing at least one query term)
        candidate_docs = set()
        for term in query_tfidf.keys():
            if term in self.indexer.inverted_index:
                for doc_id, _ in self.indexer.inverted_index[term]:
                    candidate_docs.add(doc_id)
        
        # Calculate cosine similarity for each candidate
        scores = []
        for doc_id in candidate_docs:
            score = self.cosine_similarity(query_tfidf, doc_id)
            if score > 0:
                scores.append((doc_id, score))
        
        # Sort by score descending and return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]
    
    def search_optimized(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Optimized search using heap for top-k retrieval.
        More efficient when k << number of candidates.
        
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
        
        # Calculate query TF-IDF
        query_tfidf = self.calculate_query_tfidf(query_terms)
        
        if not query_tfidf:
            return []
        
        # Find candidate documents
        candidate_docs = set()
        for term in query_tfidf.keys():
            if term in self.indexer.inverted_index:
                for doc_id, _ in self.indexer.inverted_index[term]:
                    candidate_docs.add(doc_id)
        
        # Use min-heap to maintain top-k
        # Heap stores (-score, doc_id) for max-heap behavior
        heap = []
        
        for doc_id in candidate_docs:
            score = self.cosine_similarity(query_tfidf, doc_id)
            if score > 0:
                if len(heap) < top_k:
                    heapq.heappush(heap, (score, doc_id))
                elif score > heap[0][0]:
                    heapq.heapreplace(heap, (score, doc_id))
        
        # Extract results and sort descending
        results = [(doc_id, score) for score, doc_id in heap]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def explain_query(self, query: str, doc_id: int) -> Dict:
        """
        Explain why a document matches a query (for debugging).
        
        Args:
            query: Search query
            doc_id: Document ID
            
        Returns:
            Explanation dictionary
        """
        query_terms = self.preprocessor.preprocess(query)
        query_tfidf = self.calculate_query_tfidf(query_terms)
        
        explanation = {
            'query': query,
            'query_terms': query_terms,
            'doc_id': doc_id,
            'matching_terms': {},
            'score': 0.0
        }
        
        for term, query_weight in query_tfidf.items():
            if term in self.indexer.inverted_index:
                for doc, doc_weight in self.indexer.inverted_index[term]:
                    if doc == doc_id:
                        explanation['matching_terms'][term] = {
                            'query_weight': query_weight,
                            'doc_weight': doc_weight,
                            'contribution': query_weight * doc_weight
                        }
                        break
        
        explanation['score'] = self.cosine_similarity(query_tfidf, doc_id)
        
        return explanation


# Example usage
if __name__ == "__main__":
    # Build sample index
    documents = [
        (1, "The quick brown fox jumps over the lazy dog"),
        (2, "A quick brown dog outpaces a quick fox"),
        (3, "The lazy cat sleeps all day long"),
        (4, "Dogs and cats are popular pets"),
        (5, "The fox is a clever animal")
    ]
    
    indexer = SPIMIIndexer(index_dir="data/test_index", block_size=2)
    indexer.build_index(documents)
    
    # Create query processor
    query_processor = QueryProcessor(indexer)
    
    # Test queries
    queries = [
        "quick fox",
        "lazy dog",
        "cats and dogs"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = query_processor.search(query, top_k=3)
        
        for rank, (doc_id, score) in enumerate(results, 1):
            print(f"  {rank}. Doc {doc_id}: {score:.4f}")
            
            # Show explanation for top result
            if rank == 1:
                explanation = query_processor.explain_query(query, doc_id)
                print(f"     Matching terms: {list(explanation['matching_terms'].keys())}")
