"""
Text Search Endpoints with PostgreSQL Comparison
"""

from fastapi import UploadFile, File, Form
from typing import Optional, List
import os
import time
import csv

from src.text_search.spimi_indexer import SPIMIIndexer
from src.text_search.query_processor import QueryProcessor
from src.text_search.postgres_search import PostgreSQLTextSearch
from pydantic import BaseModel


# Global text search instances
text_indexer: Optional[SPIMIIndexer] = None
text_query_processor: Optional[QueryProcessor] = None
postgres_search: Optional[PostgreSQLTextSearch] = None


class TextDocument(BaseModel):
    doc_id: int
    text: str


class TextSearchRequest(BaseModel):
    query: str
    top_k: int = 10


def register_text_search_routes(app, DATA_DIR):
    """Register text search endpoints to the FastAPI app"""
    
    @app.post("/text/build_index")
    def build_text_index(
        file: UploadFile = File(...),
        index_name: str = Form("default"),
        block_size: int = Form(1000)
    ):
        """
        Build text search index from uploaded CSV file.
        CSV should have columns: doc_id, text
        """
        global text_indexer, text_query_processor
        
        try:
            # Setup directories
            index_dir = os.path.join(DATA_DIR, f"text_index_{index_name}")
            os.makedirs(index_dir, exist_ok=True)
            
            # Save uploaded file
            csv_path = os.path.join(index_dir, "documents.csv")
            with open(csv_path, "wb") as buffer:
                import shutil
                shutil.copyfileobj(file.file, buffer)
            
            # Read CSV
            documents = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    # Try to find ID column
                    doc_id = idx  # Default to 0-based index for internal integer ID
                    
                    # Identify text column candidates
                    text_candidates = ['lyrics', 'text', 'content', 'body', 'description', 'review', 'comment', 'message', 'overview', 'summary']
                    text_column = None
                    
                    # 1. Try to find a standard text column
                    for cand in text_candidates:
                        # Case-insensitive check
                        found_col = next((k for k in row.keys() if k.lower() == cand), None)
                        if found_col:
                            text_column = found_col
                            break
                    
                    text = ""
                    if text_column:
                        text = row[text_column]
                    else:
                        # 2. Fallback: Concatenate all columns that look like text (not IDs)
                        text_parts = []
                        for k, v in row.items():
                            if 'id' not in k.lower() and 'index' not in k.lower() and 'url' not in k.lower():
                                text_parts.append(str(v))
                        text = " ".join(text_parts)
                    
                    # Extract metadata: Store ALL columns as metadata
                    metadata = row.copy()
                    
                    # Ensure we have the original text column content if we used one
                    if text_column:
                        metadata['__text_col'] = text_column
                        
                    if text.strip():
                        documents.append((doc_id, text, metadata))
            
            if not documents:
                return {"ok": False, "error": "No documents found in CSV"}
            
            # Build index
            start_time = time.time()
            text_indexer = SPIMIIndexer(index_dir=index_dir, block_size=block_size)
            text_indexer.build_index(documents)
            build_time = time.time() - start_time
            
            # Initialize query processor
            text_query_processor = QueryProcessor(indexer=text_indexer)
            
            return {
                "ok": True,
                "message": "Text index built successfully",
                "stats": {
                    "num_documents": len(documents),
                    "build_time_seconds": build_time,
                    "index_dir": index_dir
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    @app.post("/text/search")
    def search_text(request: TextSearchRequest):
        """
        Search using custom SPIMI index.
        """
        global text_query_processor
        
        try:
            if text_query_processor is None:
                return {"ok": False, "error": "Index not loaded. Build index first."}
            
            start_time = time.time()
            results = text_query_processor.search(request.query, top_k=request.top_k)
            search_time = time.time() - start_time
            
            # Format results as list of dicts with rank and text
            formatted_results = []
            for rank, (doc_id, score) in enumerate(results, 1):
                # Get document text from metadata
                doc_text = ""
                metadata = {}
                if doc_id in text_indexer.doc_metadata:
                    doc_meta = text_indexer.doc_metadata[doc_id]
                    doc_text = doc_meta.get('text', '')
                    # Truncate to first 200 characters for preview
                    if len(doc_text) > 200:
                        doc_text = doc_text[:200] + "..."
                    
                    # Extract extra metadata dynamically
                    system_fields = ['length', 'unique_terms', 'text', 'norm']
                    for k, v in doc_meta.items():
                        if k not in system_fields:
                            metadata[k] = v
                
                formatted_results.append({
                    "rank": rank,
                    "doc_id": doc_id,
                    "score": score,
                    "text": doc_text,
                    **metadata
                })
            
            return {
                "ok": True,
                "results": formatted_results,
                "search_time_seconds": search_time,
                "query": request.query
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    @app.post("/text/postgres/setup")
    def setup_postgres(
        host: str = Form("localhost"),
        database: str = Form("proyecto_bd2"),
        user: str = Form("postgres"),
        password: str = Form("postgres"),
        port: int = Form(5432)
    ):
        """
        Setup PostgreSQL connection and create table.
        """
        global postgres_search
        
        try:
            connection_params = {
                'host': host,
                'database': database,
                'user': user,
                'password': password,
                'port': port
            }
            
            postgres_search = PostgreSQLTextSearch(connection_params)
            
            if not postgres_search.connect():
                return {"ok": False, "error": "Failed to connect to PostgreSQL"}
            
            if not postgres_search.create_table():
                return {"ok": False, "error": "Failed to create table"}
            
            return {
                "ok": True,
                "message": "PostgreSQL setup successful",
                "connection": f"{user}@{host}:{port}/{database}"
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    @app.post("/text/postgres/load_data")
    def load_data_postgres(
        file: UploadFile = File(...)
    ):
        """
        Load documents into PostgreSQL from CSV.
        """
        global postgres_search
        
        try:
            if postgres_search is None:
                return {"ok": False, "error": "PostgreSQL not setup. Call /text/postgres/setup first."}
            
            # Save and read CSV
            temp_path = os.path.join(DATA_DIR, f"temp_{file.filename}")
            with open(temp_path, "wb") as buffer:
                import shutil
                shutil.copyfileobj(file.file, buffer)
            
            documents = []
            with open(temp_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    doc_id = int(row.get('doc_id', row.get('id', 0)))
                    text = row.get('text', row.get('content', ''))
                    documents.append({'doc_id': doc_id, 'text': text})
            
            os.remove(temp_path)
            
            if not documents:
                return {"ok": False, "error": "No documents found in CSV"}
            
            # Clear existing data and insert
            postgres_search.clear_table()
            start_time = time.time()
            postgres_search.insert_documents(documents)
            load_time = time.time() - start_time
            
            stats = postgres_search.get_stats()
            
            return {
                "ok": True,
                "message": "Data loaded into PostgreSQL",
                "stats": {
                    "num_documents": len(documents),
                    "load_time_seconds": load_time,
                    **stats
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    @app.post("/text/postgres/search")
    def search_postgres(request: TextSearchRequest):
        """
        Search using PostgreSQL tsvector/tsquery.
        """
        global postgres_search
        
        try:
            if postgres_search is None:
                return {"ok": False, "error": "PostgreSQL not setup"}
            
            results, search_time = postgres_search.search(request.query, top_k=request.top_k)
            
            return {
                "ok": True,
                "results": results,
                "search_time_seconds": search_time,
                "query": request.query
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    @app.post("/text/compare")
    def compare_text_search(request: TextSearchRequest):
        """
        Compare custom index vs PostgreSQL for text search.
        """
        global text_query_processor, postgres_search
        
        try:
            if text_query_processor is None:
                return {"ok": False, "error": "Custom index not loaded"}
            
            if postgres_search is None:
                return {"ok": False, "error": "PostgreSQL not setup"}
            
            # Search with custom index
            start_custom = time.time()
            results_custom = text_query_processor.search(request.query, top_k=request.top_k)
            time_custom = time.time() - start_custom
            
            # Search with PostgreSQL
            results_pg, time_pg = postgres_search.search(request.query, top_k=request.top_k)
            
            return {
                "ok": True,
                "custom_index": {
                    "time_seconds": time_custom,
                    "results": results_custom
                },
                "postgresql": {
                    "time_seconds": time_pg,
                    "results": results_pg
                },
                "speedup": time_pg / time_custom if time_custom > 0 else 0,
                "query": request.query
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
