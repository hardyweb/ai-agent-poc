"""
Memory Manager - SQLite-based persistent memory for AI Agent
Menyimpan maklumat pengguna merentas sesi.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manage user memories in SQLite database.
    Provides persistent storage for user profiles and key-value memories.
    """

    def __init__(self, user_id: str = "default"):
        """Initialize memory manager untuk user tertentu."""
        self.user_id = user_id
        self.db_path = self._get_db_path()
        self._init_database()
        logger.info(f"MemoryManager initialized for user: {user_id}")

    def _get_db_path(self) -> Path:
        """Get path to memories database."""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        return data_dir / "memories.db"

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Create tables if not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                display_name TEXT,
                total_sessions INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                memory_type TEXT DEFAULT 'fact',
                source TEXT DEFAULT 'user_stated',
                confidence REAL DEFAULT 1.0,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)

        conn.commit()
        conn.close()
        logger.debug(f"Tables initialized at {self.db_path}")

    def get_profile(self) -> Dict:
        """Return user profile."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT display_name, total_sessions, total_messages, last_seen_at, created_at
            FROM user_profiles WHERE user_id = ?
        """,
            (self.user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "display_name": row["display_name"],
                "total_sessions": row["total_sessions"],
                "total_messages": row["total_messages"],
                "last_seen_at": row["last_seen_at"],
                "created_at": row["created_at"],
            }

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_profiles (user_id, total_sessions)
            VALUES (?, 1)
        """,
            (self.user_id,),
        )
        conn.commit()
        conn.close()

        return {
            "display_name": None,
            "total_sessions": 1,
            "total_messages": 0,
            "last_seen_at": None,
            "created_at": datetime.now().isoformat(),
        }

    def get_display_name(self) -> Optional[str]:
        """Get display name from profile or memories."""
        profile = self.get_profile()
        if profile.get("display_name"):
            return profile["display_name"]

        memories = self.get_all_memories()
        for mem in memories:
            if mem["key"] in ["nama", "name", "user_name", "display_name"]:
                return mem["value"]

        return None

    def get_all_memories(self) -> List[Dict]:
        """Return all memories for this user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT key, value, memory_type, source, confidence, category, created_at, updated_at
            FROM user_memories WHERE user_id = ?
            ORDER BY created_at DESC
        """,
            (self.user_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        memories = []
        for row in rows:
            memories.append(
                {
                    "key": row["key"],
                    "value": row["value"],
                    "type": row["memory_type"],
                    "source": row["source"],
                    "confidence": row["confidence"],
                    "category": row["category"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return memories

    def remember(self, key: str, value: str, **kwargs) -> bool:
        """
        Upsert memory into database.

        Args:
            key: Memory key (unique identifier)
            value: Memory value
            kwargs: Optional params - memory_type, source, confidence, category

        Returns:
            bool: True if successful
        """
        memory_type = kwargs.get("memory_type", "fact")
        source = kwargs.get("source", "user_stated")
        confidence = kwargs.get("confidence", 1.0)
        category = kwargs.get("category", "general")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_memories (user_id, key, value, memory_type, source, confidence, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                memory_type = excluded.memory_type,
                source = excluded.source,
                confidence = excluded.confidence,
                category = excluded.category,
                updated_at = CURRENT_TIMESTAMP
        """,
            (self.user_id, key, value, memory_type, source, confidence, category),
        )

        conn.commit()
        conn.close()

        logger.info(f"Remembered: {key} = {value}")
        return True

    def forget(self, key: str) -> bool:
        """Delete specific memory by key."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM user_memories WHERE user_id = ? AND key = ?
        """,
            (self.user_id, key),
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            logger.info(f"Forgotten: {key}")

        return deleted

    def forget_all(self) -> bool:
        """Clear ALL memories for user (use with caution!)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM user_memories WHERE user_id = ?
        """,
            (self.user_id,),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.warning(f"Cleared {deleted} memories for user: {self.user_id}")
        return True

    def build_context_string(self, max_tokens: int = 300) -> str:
        """Format memories as injectable context string."""
        profile = self.get_profile()
        memories = self.get_all_memories()

        display_name = self.get_display_name()

        if not display_name and not memories:
            return ""

        lines = []
        lines.append("---")
        lines.append("User Profile")

        if display_name:
            lines.append(f"Name: {display_name}")

        lines.append(f"Sessions: {profile['total_sessions']}")

        if memories:
            lines.append("")
            lines.append("Known Facts")

            for mem in memories:
                if mem["type"] == "fact":
                    lines.append(f"{mem['key']}: {mem['value']}")

        context = "\n".join(lines)

        if len(context) > max_tokens * 4:
            context = context[: max_tokens * 4] + "..."

        return context

    def update_last_seen(self):
        """Update last_seen_at timestamp and increment counters."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_profiles
            SET last_seen_at = CURRENT_TIMESTAMP,
                total_sessions = total_sessions + 1
            WHERE user_id = ?
        """,
            (self.user_id,),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO user_profiles (user_id, total_sessions, last_seen_at)
                VALUES (?, 1, CURRENT_TIMESTAMP)
            """,
                (self.user_id,),
            )

        conn.commit()
        conn.close()

    def increment_messages(self):
        """Increment total_messages counter."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_profiles
            SET total_messages = total_messages + 1
            WHERE user_id = ?
        """,
            (self.user_id,),
        )

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Return memory statistics."""
        profile = self.get_profile()
        memories = self.get_all_memories()

        return {
            "user_id": self.user_id,
            "total_sessions": profile["total_sessions"],
            "total_messages": profile["total_messages"],
            "total_memories": len(memories),
            "last_seen_at": profile["last_seen_at"],
        }
