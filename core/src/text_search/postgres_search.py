"""
PostgreSQL Text Search Comparison Module
Uses tsvector and tsquery for full-text search comparison.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import time


class PostgreSQLTextSearch:
    """
    Wrapper for PostgreSQL full-text search using tsvector/tsquery.
    """
    
    def __init__(self, connection_params: Optional[Dict] = None):
        """
        Initialize PostgreSQL connection.
        
        Args:
            connection_params: Dict with host, database, user, password, port
        """
        self.connection_params = connection_params or {
            'host': 'localhost',
            'database': 'proyecto_bd2',
            'user': 'postgres',
            'password': 'postgres',
            'port': 5432
        }
        self.conn = None
        self.table_name = "text_documents"
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            print("PostgreSQL connection established")
            return True
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            return False
            
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def create_table(self):
        """Create table with tsvector column for full-text search."""
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor() as cur:
                # Create table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        doc_id INTEGER PRIMARY KEY,
                        content TEXT NOT NULL,
                        content_vector tsvector
                    )
                """)
                
                # Create GIN index on tsvector column
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_vector 
                    ON {self.table_name} USING GIN(content_vector)
                """)
                
                self.conn.commit()
                print(f"Table {self.table_name} created with tsvector index")
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating table: {e}")
            return False
            
    def clear_table(self):
        """Clear all data from table."""
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name}")
                self.conn.commit()
                print(f"Table {self.table_name} cleared")
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error clearing table: {e}")
            return False
            
    def insert_documents(self, documents: List[Dict[str, any]]):
        """
        Insert documents into PostgreSQL.
        
        Args:
            documents: List of dicts with 'doc_id' and 'text' keys
        """
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor() as cur:
                for doc in documents:
                    doc_id = doc['doc_id']
                    text = doc['text']
                    
                    # Insert with automatic tsvector generation
                    cur.execute(f"""
                        INSERT INTO {self.table_name} (doc_id, content, content_vector)
                        VALUES (%s, %s, to_tsvector('english', %s))
                        ON CONFLICT (doc_id) DO UPDATE 
                        SET content = EXCLUDED.content,
                            content_vector = EXCLUDED.content_vector
                    """, (doc_id, text, text))
                    
                self.conn.commit()
                print(f"Inserted {len(documents)} documents")
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error inserting documents: {e}")
            return False
            
    def search(self, query: str, top_k: int = 10, use_rank_cd: bool = False) -> tuple:
        """
        Search using PostgreSQL full-text search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_rank_cd: Use ts_rank_cd instead of ts_rank
            
        Returns:
            (results, search_time) where results is list of dicts
        """
        if not self.conn:
            self.connect()
            
        try:
            start_time = time.time()
            
            rank_function = "ts_rank_cd" if use_rank_cd else "ts_rank"
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        doc_id,
                        content,
                        {rank_function}(content_vector, query) AS rank
                    FROM {self.table_name}, 
                         to_tsquery('english', %s) query
                    WHERE content_vector @@ query
                    ORDER BY rank DESC
                    LIMIT %s
                """, (query, top_k))
                
                results = cur.fetchall()
                
            search_time = time.time() - start_time
            
            # Convert to list of dicts
            formatted_results = [
                {
                    'doc_id': row['doc_id'],
                    'text': row['content'],
                    'score': float(row['rank'])
                }
                for row in results
            ]
            
            return formatted_results, search_time
            
        except Exception as e:
            print(f"Error searching: {e}")
            return [], 0.0
            
    def get_stats(self) -> Dict:
        """Get database statistics."""
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
                result = cur.fetchone()
                
                return {
                    'total_documents': result['count'] if result else 0,
                    'table_name': self.table_name
                }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total_documents': 0, 'table_name': self.table_name}
