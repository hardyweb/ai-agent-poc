"""
Markdown RAG Search Module
===========================
Reads markdown files from /docs folder and searches them.
Simple but effective - no vector DB needed for POC!
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document"""
    content: str
    source: str
    section: str
    relevance_score: float


class MarkdownSearcher:
    """
    Simple RAG implementation for markdown files.
    
    Strategy:
    1. Load all .md files from /docs directory
    2. Split into chunks (by headers/paragraphs)
    3. Keyword matching with scoring
    4. Return top results
    
    No embeddings needed - using keyword overlap for simplicity!
    """
    
    def __init__(self, docs_dir: str = "./docs"):
        self.docs_dir = Path(docs_dir)
        self.documents: List[Dict] = []
        self.chunks: List[DocumentChunk] = []
        
        # Load documents on initialization
        self._load_documents()
        self._create_chunks()
    
    def _load_documents(self):
        """Load all markdown files from docs directory"""
        if not self.docs_dir.exists():
            print(f"[Warning] Docs directory not found: {self.docs_dir}")
            return
        
        for md_file in self.docs_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                self.documents.append({
                    'filename': md_file.name,
                    'path': str(md_file),
                    'content': content
                })
                print(f"✓ Loaded: {md_file.name}")
            except Exception as e:
                print(f"✗ Error loading {md_file.name}: {e}")
        
        print(f"\n📄 Total documents loaded: {len(self.documents)}")
    
    def _create_chunks(self):
        """
        Split documents into searchable chunks.
        
        Strategy:
        - Split by ## headers (H2)
        - Each chunk includes header context
        - Keep chunks manageable size (~500 chars)
        """
        for doc in self.documents:
            content = doc['content']
            filename = doc['filename']
            
            # Split by H2 headers (##)
            sections = re.split(r'\n(?=## )', content)
            
            for section in sections[:20]:  # Limit sections per doc
                # Clean up the section text
                clean_text = section.strip()
                
                if len(clean_text) > 50:  # Skip very short sections
                    # Extract section title (first line starting with #)
                    title_match = re.match(r'^(#+)\s+(.+)$', clean_text)
                    section_title = title_match.group(2) if title_match else "Introduction"
                    
                    # Truncate if too long
                    if len(clean_text) > 1000:
                        clean_text = clean_text[:1000] + "..."
                    
                    self.chunks.append(DocumentChunk(
                        content=clean_text,
                        source=filename,
                        section=section_title,
                        relevance_score=0.0
                    ))
        
        print(f"📦 Total chunks created: {len(self.chunks)}\n")
    
    def _calculate_relevance(self, query: str, chunk: DocumentChunk) -> float:
        """
        Calculate relevance score between query and chunk.
        
        Simple algorithm:
        - Keyword matching (exact + partial)
        - Title boost (matches in title score higher)
        - Length penalty (shorter, more focused chunks preferred)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        content_lower = chunk.content.lower()
        section_lower = chunk.section.lower()
        
        score = 0.0
        
        # Exact phrase match (big bonus)
        if query_lower in content_lower:
            score += 10.0
        
        # Word-by-word matching
        for word in query_words:
            if len(word) > 2:  # Skip short words
                # Content matches
                count = content_lower.count(word)
                score += count * 2.0
                
                # Section/title matches (bonus)
                if word in section_lower:
                    score += 3.0
        
        # Normalize by chunk length (prefer concise answers)
        if len(chunk.content) > 0:
            score = score / (len(chunk.content) / 500)
        
        return score
    
    def search(
        self, 
        query: str, 
        top_k: int = 3,
        min_score: float = 1.0
    ) -> Dict:
        """
        Search documents for relevant chunks.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            min_score: Minimum relevance threshold
        
        Returns:
            Dictionary with search results
        """
        if not self.chunks:
            return {
                "success": False,
                "error": "No documents loaded",
                "query": query,
                "results": []
            }
        
        # Score all chunks
        scored_chunks = []
        for chunk in self.chunks:
            score = self._calculate_relevance(query, chunk)
            if score >= min_score:
                scored_chunks.append((chunk, score))
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Take top_k results
        top_results = scored_chunks[:top_k]
        
        # Format results
        results = [
            {
                "content": chunk.content[:800] + "..." if len(chunk.content) > 800 else chunk.content,
                "source": chunk.source,
                "section": chunk.section,
                "score": round(score, 2)
            }
            for chunk, score in top_results
        ]
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results,
            "total_chunks_searched": len(self.chunks)
        }
    
    def list_available_docs(self) -> List[str]:
        """List all loaded document filenames"""
        return [doc['filename'] for doc in self.documents]


# Global instance (singleton pattern)
_searcher_instance: Optional[MarkdownSearcher] = None


def get_searcher() -> MarkdownSearcher:
    """Get or create searcher instance"""
    global _searcher_instance
    if _searcher_instance is None:
        _searcher_instance = MarkdownSearcher()
    return _searcher_instance


def search_markdown(query: str, top_k: int = 3) -> Dict:
    """
    Search function to be used as agent tool.
    
    This is the function that gets called by the AI Agent!
    """
    searcher = get_searcher()
    return searcher.search(query, top_k=top_k)


# Tool definition for LLM function calling
MARKDOWN_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_markdown",
        "description": "Search through markdown documentation files (guides, notes, tutorials). Use this when user asks about detailed explanations, how-to guides, or conceptual topics stored in documentation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - keywords or question about documentation content"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 3)",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    }
}
