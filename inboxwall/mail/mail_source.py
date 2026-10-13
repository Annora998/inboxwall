"""InBox Wall v2 - Mail Source (Phase 3 Hardened)."""
from typing import List, Dict
from imap_tools import MailBox

class MailSource:
    def fetch_recent(self, limit: int = 10) -> List[Dict]:
        raise NotImplementedError

class ImapMailSource(MailSource):
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def fetch_recent(self, limit: int = 10) -> List[Dict]:
        # FIX: Cap the limit to prevent memory exhaustion / DoS
        safe_limit = min(limit, 100)
        results = []
        
        with MailBox(self.host, self.port).login(self.username, self.password) as mailbox:
            # FIX: mark_seen=False preserves the "read-only" promise
            for msg in mailbox.fetch(limit=safe_limit, reverse=True, mark_seen=False):
                # FIX: Use the true RFC 2822 Message-ID as the primary key (globally unique)
                # Fallback to UID only if Message-ID is somehow missing (rare)
                primary_id = msg.message_id or f"uid-{msg.uid}"
                
                results.append({
                    "message_id": primary_id,
                    "received_at": msg.date.isoformat() if msg.date else "",
                    "sender": msg.from_,
                    "subject": msg.subject or "",
                    "html_body": msg.html or "",
                    "text_body": msg.text or ""
                })
                
        return results