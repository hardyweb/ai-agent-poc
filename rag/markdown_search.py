"""
Markdown RAG Search Module
===========================
Reads markdown files from /docs folder and searches them.
Simple but effective - no vector DB needed for POC!

ENHANCED: Now supports auto-reload and file watching!
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
    
    ENHANCED: Supports force_reload() and smart_reload()
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
    
    # ================================================================
    # NEW METHODS: Auto-Reload Feature
    # ================================================================
    
    def force_reload(self, verbose: bool = True):
        """
        Force complete reload of all markdown documents.
        
        Call this when:
        - /reload command issued
        - File watcher detects changes
        - Manual refresh needed
        
        Args:
            verbose: Print status messages
        """
        if verbose:
            print("\n" + "=" * 60)
            print("🔄 FORCE RELOADING MARKDOWN DOCUMENTS")
            print("=" * 60)
        
        # Clear existing data
        old_doc_count = len(self.documents)
        old_chunk_count = len(self.chunks)
        
        self.documents.clear()
        self.chunks.clear()
        
        # Reload from scratch
        self._load_documents()
        self._create_chunks()
        
        if verbose:
            print(f"\n✅ RELOAD COMPLETE")
            print(f"   Documents: {old_doc_count} → {len(self.documents)}")
            print(f"   Chunks: {old_chunk_count} → {len(self.chunks)}")
            print("=" * 60 + "\n")
        
        # Log the reload
        logger.info(f"🔄 Documents reloaded | Docs: {len(self.documents)}, Chunks: {len(self.chunks)}")
    
    def smart_reload(self, verbose: bool = True) -> bool:
        """
        Smart reload: check for changes first, only reload if needed.
        
        Uses FileWatcher to detect changes efficiently.
        
        Args:
            verbose: Print messages
            
        Returns:
            True if reload happened, False if no changes
        """
        try:
            from rag.file_watcher import get_watcher
            
            watcher = get_watcher()
            changes = watcher.check_for_changes()
            
            if changes:
                if verbose:
                    print(f"\n📝 Changes detected ({len(changes)}):")
                    for change in changes:
                        print(f"  • {change}")
                    print("  → Auto-reloading...\n")
                
                self.force_reload(verbose=verbose)
                return True
            else:
                # No changes, everything is fresh
                return False
                
        except Exception as e:
            logger.warning(f"Smart reload failed, falling back to check: {e}")
            # Fallback: just do a basic check
            return self._basic_change_check(verbose)
    
    def _basic_change_check(self, verbose: bool = False) -> bool:
        """
        Basic change detection without FileWatcher.
        Fallback method - compares file counts.
        """
        current_count = len(list(self.docs_dir.glob("*.md")))
        
        if current_count != len(self.documents):
            if verbose:
                print(f"📁 File count changed ({len(self.documents)} → {current_count}), reloading...")
            self.force_reload(verbose=verbose)
            return True
        
        return False
    
    def get_document_info(self) -> Dict:
        """
        Get detailed information about loaded documents.
        
        Useful for /docs command.
        """
        doc_info = {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "documents": []
        }
        
        for doc in self.documents:
            filepath = Path(doc['path'])
            
            # Get file stats
            try:
                stat = filepath.stat()
                size_kb = stat.st_size / 1024
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            except:
                size_kb = 0
                modified = "Unknown"
            
            doc_info["documents"].append({
                "filename": doc['filename'],
                "size_kb": round(size_kb, 1),
                "modified": modified,
                "content_preview": doc['content'][:100] + "..." if len(doc['content']) > 100 else doc['content']
            })
        
        return doc_info


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

def reload_markdown_documents(force: bool = False, verbose: bool = True) -> Dict:
    """
    Global function to reload markdown documents.
    
    Can be called from CLI commands or agent.
    
    Args:
        force: If True, always reload. If False, use smart reload
        verbose: Print status messages
        
    Returns:
        Status dictionary
    """
    searcher = get_searcher()
    
    if force:
        searcher.force_reload(verbose=verbose)
        return {"success": True, "action": "force_reload", "docs_loaded": len(searcher.documents)}
    else:
        reloaded = searcher.smart_reload(verbose=verbose)
        return {
            "success": True,
            "action": "smart_reload",
            "reloaded": reloaded,
            "docs_loaded": len(searcher.documents)
        }

def list_markdown_documents() -> Dict:
    """
    Get list of all loaded markdown documents.
    
    For /docs command.
    """
    searcher = get_searcher()
    info = searcher.get_document_info()
    
    return {
        "success": True,
        "total_documents": info["total_documents"],
        "total_chunks": info["total_chunks"],
        "documents": info["documents"]
    }

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
