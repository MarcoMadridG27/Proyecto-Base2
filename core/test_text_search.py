"""
Test script for text search module
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.text_search.preprocessor import TextPreprocessor
from src.text_search.spimi_indexer import SPIMIIndexer
from src.text_search.query_processor import QueryProcessor

def test_preprocessor():
    print("=" * 60)
    print("Testing Text Preprocessor")
    print("=" * 60)
    
    preprocessor = TextPreprocessor(language='english', use_stemming=True)
    
    test_texts = [
        "The quick brown foxes are running through the beautiful forest!",
        "Machine learning is transforming the world of technology",
        "Python programming language is widely used for data science"
    ]
    
    for text in test_texts:
        tokens = preprocessor.preprocess(text)
        print(f"\nOriginal: {text}")
        print(f"Tokens: {tokens}")

def test_spimi_indexer():
    print("\n" + "=" * 60)
    print("Testing SPIMI Indexer")
    print("=" * 60)
    
    # Sample documents
    documents = [
        (1, "The quick brown fox jumps over the lazy dog"),
        (2, "A quick brown dog outpaces a quick fox"),
        (3, "The lazy cat sleeps all day long"),
        (4, "Dogs and cats are popular pets"),
        (5, "The fox is a clever animal"),
        (6, "Machine learning algorithms can learn from data"),
        (7, "Python is a programming language for machine learning"),
        (8, "Data science combines statistics and programming"),
        (9, "Natural language processing is a subfield of AI"),
        (10, "Text mining extracts information from text documents")
    ]
    
    # Build index
    indexer = SPIMIIndexer(index_dir="data/test_text_index", block_size=3)
    indexer.build_index(documents)
    indexer.save_index()
    
    print(f"\nIndex Statistics:")
    print(f"  - Documents: {indexer.num_docs}")
    print(f"  - Vocabulary size: {len(indexer.vocabulary)}")
    print(f"  - Avg doc length: {indexer.avg_doc_length:.2f}")
    
    # Show some terms
    print(f"\nSample terms from index:")
    for i, term in enumerate(sorted(indexer.vocabulary)[:10]):
        postings = indexer.inverted_index[term]
        print(f"  {term}: {len(postings)} docs")

def test_query_processor():
    print("\n" + "=" * 60)
    print("Testing Query Processor")
    print("=" * 60)
    
    # Load index
    indexer = SPIMIIndexer(index_dir="data/test_text_index")
    indexer.load_index()
    
    # Create query processor
    query_processor = QueryProcessor(indexer)
    
    # Test queries
    queries = [
        "quick fox",
        "machine learning",
        "lazy dog cat",
        "programming python"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = query_processor.search(query, top_k=5)
        
        if results:
            for rank, (doc_id, score) in enumerate(results, 1):
                print(f"  {rank}. Doc {doc_id}: score={score:.4f}")
        else:
            print("  No results found")

if __name__ == "__main__":
    try:
        test_preprocessor()
        test_spimi_indexer()
        test_query_processor()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
