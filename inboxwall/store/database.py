"""InBox Wall v2 - Database Manager (Storage Security Fix)."""
import sqlite3
import contextlib
from pathlib import Path
from typing import Optional
import platform

class DatabaseManager:
    def __init__(self, base_dir: Optional[Path] = None, read_only: bool = False):
        if base_dir is None:
            if platform.system() == "Windows":
                base_dir = Path.home() / "AppData" / "Local" / "InBoxWall"
            else:
                base_dir = Path.home() / ".inboxwall" / "data"
        
        base_dir.mkdir(parents=True, exist_ok=True)
        
        self.safe_db_path = base_dir / "safemail.db"
        self.vault_db_path = base_dir / "vault.db"
        
        if not read_only:
            self._init_databases()

    def _get_connection(self, db_path: Path, read_only: bool = False):
        if read_only:
            uri = db_path.as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            
        conn.row_factory = sqlite3.Row
        
        if not read_only:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
        return contextlib.closing(conn)

    def _init_databases(self):
        with self._get_connection(self.safe_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS safe_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    uid_validity INTEGER NOT NULL,
                    uid INTEGER NOT NULL,
                    message_id TEXT,
                    received_at TEXT,
                    sender TEXT,
                    subject TEXT,
                    clean_body TEXT,
                    verdict TEXT,
                    rules_version TEXT DEFAULT 'v2.0.0',
                    UNIQUE(account, folder, uid_validity, uid)
                )
            """)
            conn.commit()
            
        with self._get_connection(self.vault_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threat_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    safe_email_id INTEGER,
                    finding_kind TEXT,
                    full_text TEXT,
                    position TEXT,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (safe_email_id) REFERENCES safe_emails(id)
                )
            """)
            conn.commit()

    def save_email(self, account: str, folder: str, uid_validity: int, uid: int,
                   message_id: str, received_at: str, sender: str, subject: str, 
                   clean_body: str, verdict: str, findings: list, rules_version: str = "v2.0.0"):
        with self._get_connection(self.safe_db_path) as conn:
            # FIX: Perform the upsert
            conn.execute("""
                INSERT INTO safe_emails 
                (account, folder, uid_validity, uid, message_id, received_at, sender, subject, clean_body, verdict, rules_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account, folder, uid_validity, uid) DO UPDATE SET
                    message_id=excluded.message_id,
                    received_at=excluded.received_at,
                    sender=excluded.sender,
                    subject=excluded.subject,
                    clean_body=excluded.clean_body,
                    verdict=excluded.verdict,
                    rules_version=excluded.rules_version
            """, (account, folder, uid_validity, uid, message_id, received_at, sender, subject, clean_body, verdict, rules_version))
            
            # FIX: Retrieve the actual ID after the upsert (works for both INSERT and UPDATE)
            cursor = conn.execute(
                "SELECT id FROM safe_emails WHERE account=? AND folder=? AND uid_validity=? AND uid=?",
                (account, folder, uid_validity, uid)
            )
            safe_email_id = cursor.fetchone()["id"]
            conn.commit()

        if findings:
            with self._get_connection(self.vault_db_path) as conn:
                # Delete old vault entries before inserting new ones
                conn.execute("DELETE FROM threat_vault WHERE safe_email_id = ?", (safe_email_id,))
                
                vault_data = [
                    (safe_email_id, f.kind, f.full_text, f.position) 
                    for f in findings
                ]
                conn.executemany("""
                    INSERT INTO threat_vault (safe_email_id, finding_kind, full_text, position)
                    VALUES (?, ?, ?, ?)
                """, vault_data)
                conn.commit()

    def get_safe_email(self, safe_email_id: int) -> Optional[dict]:
        with self._get_connection(self.safe_db_path, read_only=True) as conn:
            cursor = conn.execute(
                "SELECT * FROM safe_emails WHERE id = ?", 
                (safe_email_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None