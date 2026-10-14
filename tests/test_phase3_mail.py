"""Professional Test Suite for Phase 3 Mail & Storage."""
import sys, os, shutil
sys.path.insert(0, os.getcwd())

from unittest.mock import MagicMock, patch
from inboxwall.mail.mail_source import ImapMailSource
from inboxwall.processor import EmailProcessor, RULES_VERSION
from inboxwall.store.database import DatabaseManager
from pathlib import Path

def test_phase3():
    source = ImapMailSource("imap.test.com", 993, "user@test.com", "pw")
    with patch('inboxwall.mail.mail_source.MailBox') as MockMailBox:
        mock_instance = MockMailBox.return_value.login.return_value.__enter__.return_value
        mock_msg = MagicMock()
        mock_msg.message_id = "<unique-123@test.com>"
        mock_msg.uid = "999"
        mock_msg.date.isoformat.return_value = "2026-10-12T10:00:00"
        mock_msg.from_ = "sender@test.com"
        mock_msg.subject = "Test"
        mock_msg.html = "<p>Hi</p>"
        mock_msg.text = "Hi"
        mock_instance.fetch.return_value = [mock_msg]

        results = source.fetch_recent(limit=5)

        call_kwargs = mock_instance.fetch.call_args[1]
        assert call_kwargs.get("mark_seen") is False
        assert results[0]["message_id"] == "<unique-123@test.com>"
        assert results[0]["account"] == "user@test.com"
        assert results[0]["folder"] == "INBOX"
        assert results[0]["uid"] == 999
        assert "uid_validity" in results[0]
        print("[PASS] Mail Source: real account/folder/UID captured, mark_seen=False.")

    test_dir = Path(__file__).resolve().parent.parent / "test_data_p3"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    mock_db = DatabaseManager(base_dir=test_dir)

    mock_source = MagicMock()
    mock_source.fetch_recent.return_value = [{
        "message_id": "<msg-002>",
        "account": "user@test.com",
        "folder": "INBOX",
        "uid_validity": 4242,
        "uid": 77,
        "received_at": "2026-10-12T10:00:00",
        "sender": "test@test.com",
        "subject": "Plain Text Only",
        "html_body": "",
        "text_body": "Hello & <script>alert(1)</script>"
    }]

    processor = EmailProcessor(mail_source=mock_source, db=mock_db)
    stats = processor.process_inbox(limit=5)
    assert stats["processed"] == 1

    with mock_db._get_connection(mock_db.safe_db_path, read_only=True) as conn:
        cursor = conn.execute("SELECT * FROM safe_emails WHERE message_id = ?", ("<msg-002>",))
        safe_email = cursor.fetchone()

    assert safe_email is not None
    assert "<script>" in safe_email["clean_body"]
    assert safe_email["rules_version"] == RULES_VERSION
    assert safe_email["uid"] == 77 and safe_email["uid_validity"] == 4242
    print("[PASS] Processor: real composite key stored, plain text safe, versioned.")
    print("\n=== All Phase 3 Mail & Storage Tests Passed! ===")

if __name__ == "__main__":
    test_phase3()