"""InBox Wall v2 - Professional Database Manager."""
import sqlite3
import contextlib
from pathlib import Path
from typing import Optional
import platform

MAX_ORIGINAL_BYTES = 200_000
ORIGINAL_RETENTION_DAYS = 30


def default_data_dir() -> Path:
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Local" / "InBoxWall"
    return Path.home() / ".inboxwall" / "data"


class DatabaseManager:
    def __init__(self, base_dir: Optional[Path] = None, read_only: bool = False):
        if base_dir is None:
            base_dir = default_data_dir()

        base_dir.mkdir(parents=True, exist_ok=True)
        try:
            base_dir.chmod(0o700)
        except Exception:
            pass

        self.safe_db_path = base_dir / "safemail.db"
        self.vault_db_path = base_dir / "vault.db"
        self.reports_dir = base_dir / "reports"

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
                    threat_score INTEGER DEFAULT 0,
                    review_status TEXT DEFAULT 'locked',
                    UNIQUE(account, folder, uid_validity, uid)
                )
            """)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(safe_emails)")}
            if "threat_score" not in cols:
                conn.execute("ALTER TABLE safe_emails ADD COLUMN threat_score INTEGER DEFAULT 0")
            if "review_status" not in cols:
                conn.execute("ALTER TABLE safe_emails ADD COLUMN review_status TEXT DEFAULT 'locked'")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_originals (
                    safe_email_id INTEGER PRIMARY KEY,
                    original_html TEXT,
                    stored_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (safe_email_id) REFERENCES safe_emails(id)
                )
            """)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(email_originals)")}
            if "stored_at" not in cols:
                # SQLite forbids non-constant defaults in ALTER; backfill instead
                conn.execute("ALTER TABLE email_originals ADD COLUMN stored_at TEXT")
                conn.execute("UPDATE email_originals SET stored_at = datetime('now') WHERE stored_at IS NULL")
            # Privacy: retention purge of quarantined originals
            conn.execute(
                "DELETE FROM email_originals WHERE stored_at IS NOT NULL AND stored_at < datetime('now', ?)",
                (f"-{ORIGINAL_RETENTION_DAYS} day",)
            )
            conn.commit()

        for p in (self.safe_db_path, self.vault_db_path):
            try:
                p.chmod(0o600)
            except Exception:
                pass

    def save_email(self, account: str, folder: str, uid_validity: int, uid: int,
                   message_id: str, received_at: str, sender: str, subject: str,
                   clean_body: str, verdict: str, findings: list,
                   rules_version: str = "v2.0.0", original_html: str = "",
                   threat_score: int = 0):
        if original_html and len(original_html.encode("utf-8", "ignore")) > MAX_ORIGINAL_BYTES:
            original_html = original_html[:MAX_ORIGINAL_BYTES] + "\n[truncated for privacy]"

        with self._get_connection(self.safe_db_path) as conn:
            conn.execute("""
                INSERT INTO safe_emails
                (account, folder, uid_validity, uid, message_id, received_at,
                 sender, subject, clean_body, verdict, rules_version, threat_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account, folder, uid_validity, uid) DO UPDATE SET
                    message_id=excluded.message_id,
                    received_at=excluded.received_at,
                    sender=excluded.sender,
                    subject=excluded.subject,
                    clean_body=excluded.clean_body,
                    verdict=excluded.verdict,
                    rules_version=excluded.rules_version,
                    threat_score=excluded.threat_score
            """, (account, folder, uid_validity, uid, message_id, received_at,
                  sender, subject, clean_body, verdict, rules_version, threat_score))

            cursor = conn.execute(
                "SELECT id FROM safe_emails WHERE account=? AND folder=? AND uid_validity=? AND uid=?",
                (account, folder, uid_validity, uid)
            )
            safe_email_id = cursor.fetchone()["id"]
            conn.commit()

        with self._get_connection(self.vault_db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO email_originals (safe_email_id, original_html, stored_at) VALUES (?, ?, datetime('now'))",
                (safe_email_id, original_html)
            )
            conn.execute("DELETE FROM threat_vault WHERE safe_email_id = ?", (safe_email_id,))
            if findings:
                vault_data = [(safe_email_id, f.kind, f.full_text, f.position) for f in findings]
                conn.executemany(
                    "INSERT INTO threat_vault (safe_email_id, finding_kind, full_text, position) VALUES (?, ?, ?, ?)",
                    vault_data
                )
            conn.commit()

    def get_safe_email(self, safe_email_id: int) -> Optional[dict]:
        with self._get_connection(self.safe_db_path, read_only=True) as conn:
            cursor = conn.execute("SELECT * FROM safe_emails WHERE id = ?", (safe_email_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_original(self, safe_email_id: int) -> Optional[dict]:
        with self._get_connection(self.vault_db_path, read_only=True) as conn:
            cursor = conn.execute(
                "SELECT original_html FROM email_originals WHERE safe_email_id = ?",
                (safe_email_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_original(self, safe_email_id: int):
        with self._get_connection(self.vault_db_path) as conn:
            conn.execute("DELETE FROM email_originals WHERE safe_email_id = ?", (safe_email_id,))
            conn.commit()

    def set_review_status(self, safe_email_id: int, status: str, verdict: Optional[str] = None):
        with self._get_connection(self.safe_db_path) as conn:
            if verdict:
                conn.execute(
                    "UPDATE safe_emails SET review_status = ?, verdict = ? WHERE id = ?",
                    (status, verdict, safe_email_id)
                )
            else:
                conn.execute(
                    "UPDATE safe_emails SET review_status = ? WHERE id = ?",
                    (status, safe_email_id)
                )
            conn.commit()

    def record_sync(self, account: str, folder: str):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection(self.safe_db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync', ?)", (now,))
            conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('mailbox', ?)", (f"{folder} ({account})",))
            conn.commit()

    def get_sync(self) -> dict:
        out = {}
        with self._get_connection(self.safe_db_path, read_only=True) as conn:
            for row in conn.execute("SELECT key, value FROM sync_meta"):
                out[row["key"]] = row["value"]
        return out