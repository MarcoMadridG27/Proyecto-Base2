
import os
import shutil
import sys
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from text_search.spimi_indexer import SPIMIIndexer
from text_search.query_processor import QueryProcessor

def log(msg):
    with open("spimi_test_log.txt", "a") as f:
        f.write(str(msg) + "\n")
    print(msg)

def test_spimi_disk():
    if os.path.exists("spimi_test_log.txt"):
        os.remove("spimi_test_log.txt")
        
    log("Testing SPIMI Disk-Based Indexing...")
    
    # Setup test directory
    index_dir = "data/test_spimi_disk"
    if os.path.exists(index_dir):
        shutil.rmtree(index_dir)
    
    # Sample documents
    documents = [
        (1, "apple banana orange", {}),
        (2, "banana orange grape", {}),
        (3, "apple grape mango", {}),
        (4, "orange mango peach", {}),
        (5, "apple banana mango", {}),
        (6, "grape peach plum", {}),
        (7, "apple plum kiwi", {}),
        (8, "banana kiwi melon", {}),
    ]
    
    # 1. Build Index
    indexer = SPIMIIndexer(index_dir=index_dir, block_size=3)
    indexer.build_index(documents)
    
    # 3. Test Query Processor
    qp = QueryProcessor(indexer)
    
    results = qp.search("apple", top_k=10)
    log(f"Query 'apple' results: {results}")
    
    # 4. Test Persistence (Load Index)
    log("Testing Persistence...")
    indexer2 = SPIMIIndexer(index_dir=index_dir)
    indexer2.load_index()
    
    qp2 = QueryProcessor(indexer2)
    results2 = qp2.search("apple", top_k=10)
    log(f"Loaded results: {results2}")
    
    if len(results) != len(results2):
        log("FAILED: Persistence results mismatch")
        return False
        
    # Check content match
    for r1, r2 in zip(results, results2):
        if r1[0] != r2[0]: # doc_id
             log(f"Mismatch doc_id: {r1} vs {r2}")
             return False
        if abs(r1[1] - r2[1]) > 0.001: # score
             log(f"Mismatch score: {r1} vs {r2}")
             return False
             
    log("SPIMI Disk Test PASSED")
    return True

if __name__ == "__main__":
    test_spimi_disk()
