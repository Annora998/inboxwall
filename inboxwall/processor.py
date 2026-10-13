"""InBox Wall v2 - Master Processor (Phase 3 Hardened)."""
import logging
import html
from typing import Dict
from inboxwall.mail.mail_source import MailSource
from inboxwall.engine.pipeline import WallPipeline
from inboxwall.store.database import DatabaseManager
from inboxwall.engine.models import Verdict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# FIX: Centralized rules version for auditing
RULES_VERSION = "v2.1.0-phase3"

class EmailProcessor:
    def __init__(self, mail_source: MailSource, db: DatabaseManager):
        self.mail_source = mail_source
        self.db = db
        self.pipeline = WallPipeline()

    def process_inbox(self, limit: int = 10) -> Dict[str, int]:
        stats = {"processed": 0, "clean": 0, "cleaned": 0, "locked_away": 0, "errors": 0}
        
        logger.info(f"Fetching up to {limit} recent emails (Read-Only mode)...")
        try:
            emails = self.mail_source.fetch_recent(limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return stats

        logger.info(f"Processing {len(emails)} emails through the Wall...")
        
        for email in emails:
            stats["processed"] += 1
            msg_id = email["message_id"]
            
            try:
                # FIX: Safe plain-text fallback. Escape HTML entities first so they render as text, 
                # then wrap in <pre>. The sanitizer will safely parse this.
                if email["html_body"]:
                    html_to_process = email["html_body"]
                else:
                    safe_text = html.escape(email["text_body"] or "")
                    html_to_process = f"<pre>{safe_text}</pre>"
                
                result = self.pipeline.process(html_to_process)
                
                # FIX 3: Sanitize metadata before saving
                safe_sender = self.pipeline.sanitize_metadata(email["sender"])
                safe_subject = self.pipeline.sanitize_metadata(email["subject"])

                # FIX: Use composite key (account, folder, uid_validity, uid)
                # For now, we use placeholder values. In production, these come from the mail source.
                account = "user@example.com"
                folder = "INBOX"
                uid_validity = 1234567890
                uid = hash(msg_id) % 1000000  # Temporary: derive UID from message_id

                self.db.save_email(
                    account=account,
                    folder=folder,
                    uid_validity=uid_validity,
                    uid=uid,
                    message_id=msg_id,
                    received_at=email["received_at"],
                    sender=safe_sender,
                    subject=safe_subject,
                    clean_body=result["clean_text"],
                    verdict=result["verdict"].value,
                    findings=result["findings"],
                    rules_version=RULES_VERSION
                )
                
                if result["verdict"] == Verdict.CLEAN:
                    stats["clean"] += 1
                elif result["verdict"] == Verdict.CLEANED:
                    stats["cleaned"] += 1
                elif result["verdict"] == Verdict.LOCKED_AWAY:
                    stats["locked_away"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                stats["errors"] += 1

        logger.info(f"Processing complete. Stats: {stats}")
        return stats