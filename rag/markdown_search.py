"""
Markdown RAG Search Module
===========================
Reads markdown files from /docs folder and searches them.
Enhanced with ChromaDB vector search support!
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
    RAG implementation for markdown files with hybrid search.

    Supports:
    - Keyword-based search (original)
    - Vector/semantic search via ChromaDB (new)
    - Hybrid search combining both (best results)
    """

    def __init__(self, docs_dir: str = "./docs"):
        """Initialize with vector search support"""
        self.docs_dir = Path(docs_dir)
        self.documents: List[Dict] = []
        self.chunks: List[DocumentChunk] = []
        self._vector_enabled = False  # Track if vector search available

        # Load documents on initialization
        self._load_documents()
        self._create_chunks()

        # Try to enable vector search
        self._enable_vector_search()

    def _load_documents(self):
        """Load all markdown files from docs directory"""
        if not self.docs_dir.exists():
            print(f"[Warning] Docs directory not found: {self.docs_dir}")
            return

        for md_file in self.docs_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self.documents.append(
                    {"filename": md_file.name, "path": str(md_file), "content": content}
                )
                print(f"✓ Loaded: {md_file.name}")
            except Exception as e:
                print(f"✗ Error loading {md_file.name}: {e}")

        print(f"\n📄 Total documents loaded: {len(self.documents)}")

    def _create_chunks(self):
        """Split documents into searchable chunks"""
        for doc in self.documents:
            content = doc["content"]
            filename = doc["filename"]

            # Split by H1 or H2 headers (# or ##)
            sections = re.split(r"\n(?=#+ )", content)

            for section in sections[:20]:  # Limit sections per doc
                clean_text = section.strip()

                if len(clean_text) > 50:  # Skip very short sections
                    # Extract section title
                    title_match = re.match(r"^(#+)\s+(.+)$", clean_text)
                    section_title = (
                        title_match.group(2) if title_match else "Introduction"
                    )

                    # Truncate if too long
                    if len(clean_text) > 1000:
                        clean_text = clean_text[:1000] + "..."

                    self.chunks.append(
                        DocumentChunk(
                            content=clean_text,
                            source=filename,
                            section=section_title,
                            relevance_score=0.0,
                        )
                    )

        print(f"📦 Total chunks created: {len(self.chunks)}\n")

    def _calculate_relevance(self, query: str, chunk: DocumentChunk) -> float:
        """Calculate relevance score between query and chunk (keyword matching)"""
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

        # Normalize by chunk length
        if len(chunk.content) > 0:
            score = score / (len(chunk.content) / 500)

        return score

    def search(self, query: str, top_k: int = 3, min_score: float = 1.0) -> Dict:
        """
        Keyword-based search (original method).
        Returns dictionary with search results.
        """
        if not self.chunks:
            return {
                "success": False,
                "error": "No documents loaded",
                "query": query,
                "results": [],
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
                "content": chunk.content[:800] + "..."
                if len(chunk.content) > 800
                else chunk.content,
                "source": chunk.source,
                "section": chunk.section,
                "score": round(score, 2),
            }
            for chunk, score in top_results
        ]

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results,
            "total_chunks_searched": len(self.chunks),
        }

    def list_available_docs(self) -> List[str]:
        """List all loaded document filenames"""
        return [doc["filename"] for doc in self.documents]

    # ================================================================
    # NEW: Vector Search Integration Methods
    # ================================================================

    def _enable_vector_search(self):
        """Attempt to enable ChromaDB vector search"""
        try:
            from tools.vector_search import get_vector_search

            vs = get_vector_search()

            # Prepare documents for indexing
            docs_to_index = []
            for idx, chunk in enumerate(self.chunks):
                docs_to_index.append(
                    {
                        "id": f"{chunk.source}_{idx}",
                        "content": chunk.content,
                        "metadata": {"source": chunk.source, "section": chunk.section},
                    }
                )

            if docs_to_index:
                count = vs.index_documents(docs_to_index)
                if count > 0:
                    self._vector_enabled = True
                    print(f"🧠 Vector search enabled: {count} chunks indexed")
                    logger.info(f"✅ Vector search enabled with {count} chunks")

        except ImportError:
            print("⚠️  ChromaDB not installed - using keyword search only")
            logger.warning("ChromaDB not available - keyword search only")

        except Exception as e:
            print(f"❌ Vector search error: {e}")
            logger.error(f"Vector search failed: {e}")

    def search_hybrid(self, query: str, top_k: int = 3) -> Dict:
        """
        Hybrid search combining keyword + vector similarity.
        BEST RESULTS - Use this!
        """
        # Step 1: Keyword search (existing method)
        keyword_result = self.search(query, top_k=top_k * 2, min_score=0.5)
        keyword_results = keyword_result.get("results", [])

        # Step 2: Vector search (if enabled)
        vector_results_raw = []
        if self._vector_enabled:
            try:
                from tools.vector_search import get_vector_search

                vs = get_vector_search()
                vector_results_raw = vs.search(query, top_k=top_k * 2)
            except Exception as e:
                logger.debug(f"Vector search unavailable: {e}")

        # Step 3: Merge and re-rank
        merged = {}

        # Process keyword results (weight: 40%)
        seen_sources = {}  # Track first occurrence per source
        for result in keyword_results:
            source = result["source"]
            # Use first match per source, or create unique key
            if source not in seen_sources:
                seen_sources[source] = result
                key = (source, result["section"])
                score = result.get("score", 0) * 0.4
                merged[key] = {
                    **result,
                    "combined_score": score,
                    "match_type": "keyword",
                }
            else:
                # Add additional high-scoring results with unique keys
                key = (source, result["section"], result.get("content", "")[:50])
                score = result.get("score", 0) * 0.4
                merged[key] = {
                    **result,
                    "combined_score": score,
                    "match_type": "keyword",
                }

        # Process vector results (weight: 60%)
        seen_vector = {}
        for v_result in vector_results_raw:
            source = v_result.source
            if source not in seen_vector:
                seen_vector[source] = v_result
                key = (v_result.source, v_result.section)
            else:
                key = (v_result.source, v_result.section, v_result.content[:50])
            score = v_result.score * 0.6

            if key in merged:
                # Boost existing entry
                merged[key]["combined_score"] += score
                merged[key]["match_type"] += "+vector"
            elif score >= 0.2:
                merged[key] = {
                    "content": v_result.content,
                    "source": v_result.source,
                    "section": v_result.section,
                    "score": round(score, 2),
                    "combined_score": round(score, 2),
                    "match_type": "vector",
                }

        # Sort by combined score
        sorted_results = sorted(
            merged.values(), key=lambda x: x["combined_score"], reverse=True
        )[:top_k]

        # Fallback: if no results from hybrid, return keyword results directly
        if not sorted_results and keyword_results:
            sorted_results = keyword_results[:top_k]

        logger.info(
            f"🔀 Hybrid: '{query[:30]}...' → {len(sorted_results)} results "
            f"(keyword: {len(keyword_results)}, vector: {len(vector_results_raw)})"
        )

        return {
            "success": True,
            "query": query,
            "count": len(sorted_results),
            "results": sorted_results,
            "search_type": "hybrid",
        }

    # ================================================================
    # Auto-Reload Feature Methods
    # ================================================================

    def force_reload(self, verbose: bool = True):
        """Force complete reload of all markdown documents"""
        if verbose:
            print("\n" + "=" * 60)
            print("🔄 FORCE RELOADING MARKDOWN DOCUMENTS")
            print("=" * 60)

        old_doc_count = len(self.documents)
        old_chunk_count = len(self.chunks)

        self.documents.clear()
        self.chunks.clear()

        self._load_documents()
        self._create_chunks()

        # Re-enable vector search with new documents
        self._enable_vector_search()

        if verbose:
            print(f"\n✅ RELOAD COMPLETE")
            print(f"   Documents: {old_doc_count} → {len(self.documents)}")
            print(f"   Chunks: {old_chunk_count} → {len(self.chunks)}")
            print("=" * 60 + "\n")

        logger.info(
            f"🔄 Documents reloaded | Docs: {len(self.documents)}, Chunks: {len(self.chunks)}"
        )

    def smart_reload(self, verbose: bool = True) -> bool:
        """Smart reload: check for changes first, only reload if needed"""
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
                return False

        except Exception as e:
            logger.warning(f"Smart reload failed: {e}")
            return self._basic_change_check(verbose)

    def _basic_change_check(self, verbose: bool = False) -> bool:
        """Basic change detection without FileWatcher"""
        current_count = len(list(self.docs_dir.glob("*.md")))

        if current_count != len(self.documents):
            if verbose:
                print(
                    f"📁 File count changed ({len(self.documents)} → {current_count}), reloading..."
                )
            self.force_reload(verbose=verbose)
            return True

        return False

    def get_document_info(self) -> Dict:
        """Get detailed information about loaded documents"""
        doc_info = {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "documents": [],
        }

        for doc in self.documents:
            filepath = Path(doc["path"])

            try:
                stat = filepath.stat()
                size_kb = stat.st_size / 1024
                modified = datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except:
                size_kb = 0
                modified = "Unknown"

            doc_info["documents"].append(
                {
                    "filename": doc["filename"],
                    "size_kb": round(size_kb, 1),
                    "modified": modified,
                    "content_preview": doc["content"][:100] + "..."
                    if len(doc["content"]) > 100
                    else doc["content"],
                }
            )

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
    Enhanced search function - uses hybrid search if available.
    Falls back to keyword-only if ChromaDB not installed.
    """
    searcher = get_searcher()

    # Use hybrid search if vector enabled, otherwise fallback to keyword
    if hasattr(searcher, "_vector_enabled") and searcher._vector_enabled:
        return searcher.search_hybrid(query, top_k=top_k)
    else:
        return searcher.search(query, top_k=top_k)


def reload_markdown_documents(force: bool = False, verbose: bool = True) -> Dict:
    """Global function to reload markdown documents"""
    searcher = get_searcher()

    if force:
        searcher.force_reload(verbose=verbose)
        return {
            "success": True,
            "action": "force_reload",
            "docs_loaded": len(searcher.documents),
        }
    else:
        reloaded = searcher.smart_reload(verbose=verbose)
        return {
            "success": True,
            "action": "smart_reload",
            "reloaded": reloaded,
            "docs_loaded": len(searcher.documents),
        }


def list_markdown_documents() -> Dict:
    """Get list of all loaded markdown documents"""
    searcher = get_searcher()
    info = searcher.get_document_info()

    return {
        "success": True,
        "total_documents": info["total_documents"],
        "total_chunks": info["total_chunks"],
        "documents": info["documents"],
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
                    "description": "Search query - keywords or question about documentation content",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 3)",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}
