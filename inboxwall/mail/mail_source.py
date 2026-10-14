"""InBox Wall v2 - Mail Source (real IMAP identity)."""
import re
from typing import List, Dict
from imap_tools import MailBox

class MailSource:
    def fetch_recent(self, limit: int = 10) -> List[Dict]:
        raise NotImplementedError

class ImapMailSource(MailSource):
    def __init__(self, host: str, port: int, username: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.folder = folder

    def _uid_validity(self, mailbox) -> int:
        """Fetch the folder's UIDVALIDITY so UIDs are globally unique."""
        # Preferred: FolderInfo attribute (imap-tools >= 1.x)
        info = getattr(mailbox, "folder", None)
        uv = getattr(info, "uid_validity", None)
        if isinstance(uv, int):
            return uv
        # Fallback: raw IMAP STATUS command
        try:
            typ, data = mailbox.client.status(f'"{self.folder}"', ["UIDVALIDITY"])
            m = re.search(rb"UIDVALIDITY\s+(\d+)", data[0])
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 0

    def fetch_recent(self, limit: int = 10) -> List[Dict]:
        safe_limit = min(limit, 100)
        results = []
        with MailBox(self.host, self.port).login(self.username, self.password) as mailbox:
            try:
                mailbox.folder.set(self.folder)
            except Exception:
                pass
            uv = self._uid_validity(mailbox)
            for msg in mailbox.fetch(limit=safe_limit, reverse=True, mark_seen=False):
                primary_id = msg.message_id or f"uid-{msg.uid}"
                try:
                    uid = int(msg.uid)
                except (TypeError, ValueError):
                    uid = 0
                results.append({
                    "message_id": primary_id,
                    "account": self.username,
                    "folder": self.folder,
                    "uid_validity": uv,
                    "uid": uid,
                    "received_at": msg.date.isoformat() if msg.date else "",
                    "sender": msg.from_,
                    "subject": msg.subject or "",
                    "html_body": msg.html or "",
                    "text_body": msg.text or "",
                })
        return results