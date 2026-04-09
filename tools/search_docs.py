"""
Search Docs Tool
================
This is the "tool" that the AI Agent can call.
It searches the SQLite knowledge base and returns relevant documents.
"""

import sqlite3
import json
from typing import Optional
from config import Config


def get_db_connection():
    """Create and return database connection"""
    conn = sqlite3.connect(str(Config.DB_PATH))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn


def search_docs(query: str, category: Optional[str] = None, limit: int = 5) -> dict:
    """
    Search documents in the knowledge base.
    
    Args:
        query: Search keywords or question
        category: Optional filter by category
        limit: Max results to return (default 5)
    
    Returns:
        Dictionary with results metadata and matched documents
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic query with FTS-like matching
        base_query = """
            SELECT id, title, content, category, source 
            FROM documents 
            WHERE 1=1
        """
        params = []
        
        # Add text search (simple LIKE matching for demo)
        if query:
            # Split query into keywords for better matching
            keywords = query.lower().split()
            conditions = []
            for kw in keywords:
                conditions.append("(LOWER(title) LIKE ? OR LOWER(content) LIKE ?)")
                params.extend([f"%{kw}%", f"%{kw}%"])
            base_query += f" AND ({' OR '.join(conditions)})"
        
        # Add category filter if specified
        if category:
            base_query += " AND category = ?"
            params.append(category)
        
        # Add limit
        base_query += f" ORDER BY id LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        # Format results
        results = [
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"][:500] + "..." if len(row["content"]) > 500 else row["content"],
                "category": row["category"],
                "source": row["source"]
            }
            for row in rows
        ]
        
        conn.close()
        
        return {
            "success": True,
            "query": query,
            "category": category,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": []
        }


def list_categories() -> dict:
    """List all available categories in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM documents ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "categories": categories
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool definition for the LLM (function calling schema)
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": "Search the knowledge base database for documents matching a query. Use this when user asks about topics stored in our documentation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - keywords or question to find relevant documents"
                },
                "category": {
                    "type": "string",
                    "enum": ["programming", "database", "api", "ai", "framework", "tutorial", "general"],
                    "description": "Optional: filter by document category"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5, max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}
