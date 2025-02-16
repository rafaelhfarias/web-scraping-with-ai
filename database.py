# database.py

import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)

class Database:
    def __init__(self, db_file: str = "links.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.create_table()

    def create_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            type TEXT,
            relevance_score REAL,
            keywords TEXT,
            metadata TEXT
        );
        """
        self.conn.execute(sql)
        self.conn.commit()
        logging.info("Table 'links' created or already exists.")

    def insert_link(self, url: str, type_: str, relevance_score: float, keywords: str, metadata: dict):
        """
        Insert a link into the database with proper type checking
        """
        try:
            sql = '''INSERT OR REPLACE INTO links
                     (url, type, relevance_score, keywords, metadata)
                     VALUES (?, ?, ?, ?, ?)'''
            
            # Ensure proper types before insertion
            url = str(url)
            type_ = str(type_)
            relevance_score = float(relevance_score)
            keywords = str(keywords)
            metadata_json = json.dumps(metadata)
            
            self.conn.execute(sql, (url, type_, relevance_score, keywords, metadata_json))
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Database insertion error: {str(e)}")
            self.conn.rollback()
        logging.info(f"Link inserted: {url} with score {relevance_score:.2f}")

    def query_links(self, keyword: str = None, type_: str = None, min_relevance: float = None) -> list:
        """
        Query links with optional filters
        """
        query = "SELECT id, url, type, relevance_score, keywords, metadata FROM links WHERE 1=1"
        params = []

        if keyword:
            query += " AND keywords = ?"
            params.append(keyword)
        
        if type_:
            query += " AND type = ?"
            params.append(type_)
        
        if min_relevance is not None:
            query += " AND relevance_score >= ?"
            params.append(min_relevance)

        query += " ORDER BY relevance_score DESC"

        try:
            cursor = self.conn.execute(query, tuple(params))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "url": row[1],
                    "type": row[2],
                    "relevance_score": row[3],
                    "keywords": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {}
                })
            return result
        except Exception as e:
            logger.error(f"Error querying links: {str(e)}")
            return []
