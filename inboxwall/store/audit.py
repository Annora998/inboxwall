"""InBox Wall v2 - AI access audit log."""
import sqlite3
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from inboxwall.store.database import default_data_dir

class AuditLogger:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = default_data_dir()
        base_dir.mkdir(parents=True, exist_ok=True)
        self.audit_db_path = base_dir / "audit.db"
        self._init()

    def _conn(self):
        conn = sqlite3.connect(str(self.audit_db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return contextlib.closing(conn)

    def _init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accessed_at TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    action TEXT NOT NULL,
                    safe_email_id INTEGER,
                    message_id TEXT,
                    outcome TEXT NOT NULL
                )
            """)
            conn.commit()

    def log(self, tool: str, action: str, safe_email_id=None, message_id=None, outcome="ok"):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO ai_access_log (accessed_at, tool, action, safe_email_id, message_id, outcome) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), tool, action, safe_email_id, message_id, outcome)
            )
            conn.commit()

    def recent(self, limit: int = 50):
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM ai_access_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]