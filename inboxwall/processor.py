"""InBox Wall v2 - Master Processor."""
import logging
import html
from typing import Dict
from inboxwall.mail.mail_source import MailSource
from inboxwall.engine.pipeline import WallPipeline
from inboxwall.store.database import DatabaseManager
from inboxwall.engine.models import Verdict

logger = logging.getLogger(__name__)
RULES_VERSION = "v2.2.0"

class EmailProcessor:
    def __init__(self, mail_source: MailSource, db: DatabaseManager):
        self.mail_source = mail_source
        self.db = db
        self.pipeline = WallPipeline()

    def process_inbox(self, limit: int = 10) -> Dict[str, int]:
        stats = {"processed": 0, "clean": 0, "cleaned": 0, "locked_away": 0, "errors": 0}
        logger.info("Fetching up to %s recent emails (Read-Only mode)...", limit)
        try:
            emails = self.mail_source.fetch_recent(limit=limit)
        except Exception as e:
            logger.error("Failed to fetch emails: %s", e)
            return stats

        logger.info("Processing %s emails through the Wall...", len(emails))
        for email in emails:
            stats["processed"] += 1
            msg_id = email["message_id"]
            try:
                if email["html_body"]:
                    html_to_process = email["html_body"]
                else:
                    safe_text = html.escape(email["text_body"] or "")
                    html_to_process = f"<pre>{safe_text}</pre>"

                result = self.pipeline.process(
                html_to_process,
                subject=email["subject"],
                sender=email["sender"]
                )
                safe_sender = result["safe_sender"]
                safe_subject = result["safe_subject"]

                # Real IMAP identity for the composite key
                account = email.get("account", "unknown")
                folder = email.get("folder", "INBOX")
                uid_validity = int(email.get("uid_validity", 0) or 0)
                uid = email.get("uid")
                if uid is None:
                    uid = abs(hash(msg_id)) % 1_000_000_000
                uid = int(uid)

                # Only real threats (weight > 0) go to the vault
                threat_findings = [f for f in result["findings"] if f.weight > 0]

                self.db.save_email(
                    account=account, folder=folder, uid_validity=uid_validity, uid=uid,
                    message_id=msg_id, received_at=email["received_at"],
                    sender=safe_sender, subject=safe_subject,
                    clean_body=result["clean_text"], verdict=result["verdict"].value,
                    findings=threat_findings, rules_version=RULES_VERSION,
                    original_html=html_to_process, threat_score=result["score"]
                )

                if result["verdict"] == Verdict.CLEAN:
                    stats["clean"] += 1
                elif result["verdict"] == Verdict.CLEANED:
                    stats["cleaned"] += 1
                elif result["verdict"] == Verdict.LOCKED_AWAY:
                    stats["locked_away"] += 1
            except Exception as e:
                logger.error("Error processing message %s: %s", msg_id, e)
                stats["errors"] += 1
        logger.info("Processing complete. Stats: %s", stats)
        return stats