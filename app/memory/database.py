import sqlite3
import os
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
import difflib

logger = structlog.get_logger(__name__)

class LocalDatabase:
    def __init__(self, db_path: str = "data/myra_local.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Table for logging all conversations, utterances, and events
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        message_type TEXT NOT NULL,
                        content TEXT NOT NULL
                    )
                """)
                # Table for storing user profile facts, preferences, and imported memories
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS saved_memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                # Table for importing project data or arbitrary structured info
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS imported_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        source TEXT NOT NULL,
                        data_payload TEXT NOT NULL,
                        imported_at TEXT NOT NULL
                    )
                """)
                # Table for messaging contacts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        app TEXT NOT NULL,
                        identifier TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                # Table for STT recognition accuracy and vocabulary boosting corrections
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS stt_corrections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        misheard_text TEXT NOT NULL,
                        corrected_text TEXT NOT NULL,
                        occurrences INTEGER DEFAULT 1,
                        last_corrected_at TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info("local_database_initialized", db_path=self.db_path)
        except Exception as e:
            logger.error("local_database_init_error", error=str(e))

    def log_conversation(self, session_id: str, sender: str, message_type: str, content: str) -> Optional[int]:
        """
        Logs an utterance or conversation event into SQLite.
        sender: 'user', 'myra', 'system', etc.
        message_type: 'text', 'audio', 'event'
        """
        try:
            timestamp = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversation_logs (session_id, timestamp, sender, message_type, content) VALUES (?, ?, ?, ?, ?)",
                    (session_id, timestamp, sender, message_type, content)
                )
                conn.commit()
                row_id = cursor.lastrowid
                logger.debug("conversation_logged", row_id=row_id, sender=sender, type=message_type)
                return row_id
        except Exception as e:
            logger.error("log_conversation_error", error=str(e))
            return None

    def get_recent_conversations(self, limit: int = 20, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves recent conversation history from the database.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if session_id:
                    cursor.execute(
                        "SELECT id, session_id, timestamp, sender, message_type, content FROM conversation_logs WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                        (session_id, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT id, session_id, timestamp, sender, message_type, content FROM conversation_logs ORDER BY id DESC LIMIT ?",
                        (limit,)
                    )
                rows = cursor.fetchall()
                # Return in chronological order
                return [dict(row) for row in reversed(rows)]
        except Exception as e:
            logger.error("get_recent_conversations_error", error=str(e))
            return []

    def search_conversations(self, query_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Searches previous conversation content for keyword matches.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, session_id, timestamp, sender, message_type, content FROM conversation_logs WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query_text}%", limit)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("search_conversations_error", error=str(e))
            return []

    def save_memory(self, key: str, value: str) -> bool:
        """
        Saves or updates an imported memory/fact.
        """
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO saved_memories (key, value, created_at, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key.lower(), value, now, now)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error("save_memory_error", error=str(e))
            return False

    def get_memory(self, key: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM saved_memories WHERE key = ?", (key.lower(),))
                row = cursor.fetchone()
                return row["value"] if row else None
        except Exception as e:
            logger.error("get_memory_error", error=str(e))
            return None

    def get_all_memories(self) -> Dict[str, str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM saved_memories ORDER BY updated_at DESC")
                rows = cursor.fetchall()
                return {row["key"]: row["value"] for row in rows}
        except Exception as e:
            logger.error("get_all_memories_error", error=str(e))
            return {}

    def import_data(self, category: str, source: str, data_payload: str) -> Optional[int]:
        try:
            timestamp = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO imported_data (category, source, data_payload, imported_at) VALUES (?, ?, ?, ?)",
                    (category, source, data_payload, timestamp)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error("import_data_error", error=str(e))
            return None

    def add_contact(self, name: str, app: str, identifier: str) -> Optional[int]:
        try:
            timestamp = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO contacts (name, app, identifier, created_at) VALUES (?, ?, ?, ?)",
                    (name, app.lower(), identifier, timestamp)
                )
                conn.commit()
                row_id = cursor.lastrowid
                logger.info("contact_added", id=row_id, name=name, app=app, identifier=identifier)
                return row_id
        except Exception as e:
            logger.error("add_contact_error", error=str(e))
            return None

    def resolve_contact(self, name: str, app: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if app:
                    cursor.execute("SELECT id, name, app, identifier, created_at FROM contacts WHERE app = ?", (app.lower(),))
                else:
                    cursor.execute("SELECT id, name, app, identifier, created_at FROM contacts")
                rows = [dict(r) for r in cursor.fetchall()]
                
                if not rows:
                    if app: # fallback to searching across any app if specific app yielded nothing
                        cursor.execute("SELECT id, name, app, identifier, created_at FROM contacts")
                        rows = [dict(r) for r in cursor.fetchall()]
                    if not rows:
                        return None

                query = name.strip().lower()
                
                # 1. Exact case-insensitive match
                for row in rows:
                    if row["name"].lower() == query:
                        return row
                        
                # 2. Substring match
                for row in rows:
                    if query in row["name"].lower() or row["name"].lower() in query:
                        return row
                        
                # 3. Fuzzy similarity match
                names = [r["name"].lower() for r in rows]
                matches = difflib.get_close_matches(query, names, n=1, cutoff=0.4)
                if matches:
                    matched_name = matches[0]
                    for row in rows:
                        if row["name"].lower() == matched_name:
                            return row
                return None
        except Exception as e:
            logger.error("resolve_contact_error", error=str(e))
            return None

    def get_all_contacts(self, app: Optional[str] = None) -> list:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if app:
                    cursor.execute("SELECT id, name, app, identifier, created_at FROM contacts WHERE app = ? ORDER BY name ASC", (app.lower(),))
                else:
                    cursor.execute("SELECT id, name, app, identifier, created_at FROM contacts ORDER BY name ASC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_all_contacts_error", error=str(e))
            return []

    def log_stt_correction(self, misheard: str, corrected: str) -> bool:
        """Logs user corrections to improve speech recognition accuracy over time."""
        try:
            timestamp = datetime.now().isoformat()
            misheard_clean = misheard.strip().lower()
            corrected_clean = corrected.strip()
            if not misheard_clean or not corrected_clean:
                return False
                
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, occurrences FROM stt_corrections WHERE LOWER(misheard_text) = ? AND LOWER(corrected_text) = ?",
                    (misheard_clean, corrected_clean.lower())
                )
                existing = cursor.fetchone()
                if existing:
                    new_count = existing["occurrences"] + 1
                    cursor.execute(
                        "UPDATE stt_corrections SET occurrences = ?, last_corrected_at = ? WHERE id = ?",
                        (new_count, timestamp, existing["id"])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO stt_corrections (misheard_text, corrected_text, occurrences, last_corrected_at) VALUES (?, ?, 1, ?)",
                        (misheard_clean, corrected_clean, timestamp)
                    )
                conn.commit()
                logger.info("stt_correction_logged", misheard=misheard_clean, corrected=corrected_clean)
                return True
        except Exception as e:
            logger.error("log_stt_correction_error", error=str(e))
            return False

    def get_stt_corrections(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves learned STT word correction pairs."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, misheard_text, corrected_text, occurrences, last_corrected_at FROM stt_corrections ORDER BY occurrences DESC, last_corrected_at DESC LIMIT ?",
                    (limit,)
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("get_stt_corrections_error", error=str(e))
            return []

    def build_custom_hotwords(self) -> List[str]:
        """
        Compiles custom speech vocabulary boosting hints from contact names, wake phrase,
        frequently used technical project terms, and learned user corrections.
        """
        hotwords = set()
        # 1. Add core technical and brand vocabulary
        core_terms = ["Myra", "WhatsApp", "Messenger", "Telegram", "Playwright", "Python", "SQLite", "ChromaDB", "Bangla", "Gemini"]
        hotwords.update(core_terms)
        
        # 2. Add wake phrase words
        from app.config import settings
        if settings.secret_wake_phrase:
            for word in settings.secret_wake_phrase.split():
                if len(word) > 2:
                    hotwords.add(word.capitalize())
                    
        # 3. Add contact names from database
        contacts = self.get_all_contacts()
        for c in contacts:
            name = c.get("name", "").strip()
            if name:
                hotwords.add(name)
                for part in name.split():
                    if len(part) > 1:
                        hotwords.add(part)
                        
        # 4. Add learned STT corrections
        corrections = self.get_stt_corrections(limit=50)
        for corr in corrections:
            hotwords.add(corr["corrected_text"])
            
        logger.debug("custom_hotwords_built", count=len(hotwords))
        return sorted(list(hotwords))
