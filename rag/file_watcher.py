"""
File Watcher Module - Monitor docs/ folder for changes
======================================================
Detects:
- New .md files added
- Existing files modified/deleted
- Provides change notifications to MarkdownSearcher
"""

import os
import time
from pathlib import Path
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class FileChange:
    """Represents a single file change event"""
    filename: str
    filepath: str
    change_type: str  # 'added', 'modified', 'deleted'
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"[{self.change_type.upper()}] {self.filename}"

class FileWatcher:
    """
    Watches a directory for file changes.
    
    Strategy:
    1. Track file modification times (mtime)
    2. Compare current state vs last known state
    3. Report only CHANGES (not full reload)
    
    Uses polling (simple, no extra dependencies like watchdog)
    """
    
    def __init__(self, watch_dir: str = "./docs", poll_interval: float = 2.0):
        """
        Initialize file watcher.
        
        Args:
            watch_dir: Directory to monitor (default: ./docs)
            poll_interval: How often to check for changes (seconds)
        """
        self.watch_dir = Path(watch_dir)
        self.poll_interval = poll_interval
        
        # Track file states: {filename: mtime_timestamp}
        self.file_states: Dict[str, float] = {}
        
        # Track what we've seen (for detecting deletions)
        self.known_files: Set[str] = set()
        
        # Change history (for debugging)
        self.change_history: List[FileChange] = []
        
        # Statistics
        self.total_changes_detected = 0
        self.last_check_time: Optional[datetime] = None
        
        # Initialize by scanning directory
        self._scan_directory()
        
        logger.info(f"👁️ FileWatcher initialized | Watching: {self.watch_dir}")
        logger.info(f"   Initial files found: {len(self.known_files)}")
    
    def _scan_directory(self):
        """Scan directory and record current file states"""
        if not self.watch_dir.exists():
            logger.warning(f"Watch directory not found: {self.watch_dir}")
            return
        
        # Get all .md files
        current_files = set()
        for md_file in self.watch_dir.glob("*.md"):
            try:
                mtime = md_file.stat().st_mtime
                filename = md_file.name
                
                self.file_states[filename] = mtime
                current_files.add(filename)
                
            except Exception as e:
                logger.error(f"Error reading {md_file}: {e}")
        
        self.known_files = current_files
        self.last_check_time = datetime.now()
    
    def check_for_changes(self) -> List[FileChange]:
        """
        Check for file changes since last scan.
        
        Returns:
            List of FileChange objects (empty if no changes)
        """
        if not self.watch_dir.exists():
            return []
        
        changes = []
        current_files = set()
        
        # Scan current state
        for md_file in self.watch_dir.glob("*.md"):
            try:
                mtime = md_file.stat().st_mtime
                filename = md_file.name
                current_files.add(filename)
                
                # CHECK 1: New file?
                if filename not in self.known_files:
                    change = FileChange(
                        filename=filename,
                        filepath=str(md_file),
                        change_type='added'
                    )
                    changes.append(change)
                    logger.info(f"🆕 NEW FILE: {filename}")
                
                # CHECK 2: Modified file?
                elif filename in self.file_states:
                    old_mtime = self.file_states[filename]
                    if mtime > old_mtime:
                        change = FileChange(
                            filename=filename,
                            filepath=str(md_file),
                            change_type='modified'
                        )
                        changes.append(change)
                        logger.info(f"✏️ MODIFIED: {filename}")
                    
                    # Update stored mtime regardless
                    self.file_states[filename] = mtime
                    
            except Exception as e:
                logger.error(f"Error checking {md_file}: {e}")
        
        # CHECK 3: Deleted files?
        deleted_files = self.known_files - current_files
        for filename in deleted_files:
            change = FileChange(
                filename=filename,
                filepath=str(self.watch_dir / filename),
                change_type='deleted'
            )
            changes.append(change)
            logger.info(f"🗑️ DELETED: {filename}")
            
            # Remove from tracking
            if filename in self.file_states:
                del self.file_states[filename]
        
        # Update known files
        self.known_files = current_files
        self.last_check_time = datetime.now()
        
        # Record changes
        if changes:
            self.change_history.extend(changes)
            self.total_changes_detected += len(changes)
        
        return changes
    
    def has_changes(self) -> bool:
        """Quick check: are there any pending changes?"""
        return len(self.check_for_changes()) > 0
    
    def get_file_count(self) -> int:
        """Return number of tracked files"""
        return len(self.known_files)
    
    def list_tracked_files(self) -> List[str]:
        """List all currently tracked filenames"""
        return sorted(list(self.known_files))
    
    def get_stats(self) -> Dict:
        """Return watcher statistics"""
        return {
            "watch_dir": str(self.watch_dir),
            "files_tracked": len(self.known_files),
            "total_changes_detected": self.total_changes_detected,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "recent_changes": [str(c) for c in self.change_history[-5:]]  # Last 5 changes
        }
    
    def reset(self):
        """Reset watcher state (force full rescan on next check)"""
        self.file_states.clear()
        self.known_files.clear()
        self._scan_directory()
        logger.info("🔄 FileWatcher reset - rescanned directory")


# Global instance (singleton pattern)
_watcher_instance: Optional[FileWatcher] = None

def get_watcher() -> FileWatcher:
    """Get or create global FileWatcher instance"""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = FileWatcher()
    return _watcher_instance


# Convenience function for quick checks
def check_docs_changed() -> bool:
    """
    Quick check if any markdown files changed.
    Can be called before searches to decide if reload needed.
    """
    watcher = get_watcher()
    return watcher.has_changes()


if __name__ == "__main__":
    # Test the file watcher
    print("=" * 60)
    print("FILE WATCHER TEST")
    print("=" * 60)
    
    watcher = FileWatcher("./docs")
    
    print(f"\n📁 Watching: {watcher.watch_dir}")
    print(f"📄 Files found: {watcher.get_file_count()}")
    print(f"\n📋 Tracked files:")
    for f in watcher.list_tracked_files():
        print(f"  - {f}")
    
    print("\n⏳ Checking for changes...")
    changes = watcher.check_for_changes()
    
    if changes:
        print(f"\n✅ Changes detected: {len(changes)}")
        for change in changes:
            print(f"  {change}")
    else:
        print("\n✅ No changes detected (expected on first run)")
    
    print(f"\n📊 Stats: {watcher.get_stats()}")
