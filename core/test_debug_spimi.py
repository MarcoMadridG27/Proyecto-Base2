
import os
import shutil
import sys
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from text_search.spimi_indexer import SPIMIIndexer

def log(msg):
    with open("debug_log.txt", "a") as f:
        f.write(msg + "\n")
    print(msg)

def test_debug_persistence():
    if os.path.exists("debug_log.txt"):
        os.remove("debug_log.txt")
        
    log("Testing Debug Persistence...")
    
    index_dir = "data/test_debug"
    if os.path.exists(index_dir):
        shutil.rmtree(index_dir)
    
    documents = [
        (1, "apple", {}),
    ]
    
    # Build
    indexer = SPIMIIndexer(index_dir=index_dir, block_size=10)
    indexer.build_index(documents)
    
    term = "appl" # Stemmed apple
    
    log(f"\n--- Indexer 1 ---")
    if term in indexer.vocabulary:
        off = indexer.vocabulary[term]
        log(f"Vocab offset: {off}")
        postings = indexer.get_postings(term)
        log(f"Postings: {postings}")
    else:
        log(f"Term {term} not in vocab")
        
    indexer.close()
    
    log(f"\n--- Indexer 2 (Loaded) ---")
    indexer2 = SPIMIIndexer(index_dir=index_dir)
    indexer2.load_index()
    
    if term in indexer2.vocabulary:
        off = indexer2.vocabulary[term]
        log(f"Vocab offset: {off}")
        postings = indexer2.get_postings(term)
        log(f"Postings: {postings}")
    else:
        log(f"Term {term} not in vocab")
        
    indexer2.close()

if __name__ == "__main__":
    test_debug_persistence()
