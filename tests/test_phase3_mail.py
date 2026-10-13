"""Professional Test Suite for Phase 3 Mail & Storage."""
import sys, os
sys.path.insert(0, os.getcwd())

from unittest.mock import MagicMock, patch
from inboxwall.mail.mail_source import ImapMailSource
from inboxwall.processor import EmailProcessor, RULES_VERSION
from inboxwall.store.database import DatabaseManager
from pathlib import Path

def test_phase3():
    # 1. Test Mail Source Limits and mark_seen
    source = ImapMailSource("imap.test.com", 993, "u", "p")
    with patch('inboxwall.mail.mail_source.MailBox') as MockMailBox:
        mock_login = MockMailBox.return_value.login.return_value
        mock_instance = mock_login.__enter__.return_value
        
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
        
        # Verify mark_seen=False was passed
        call_kwargs = mock_instance.fetch.call_args[1]
        assert call_kwargs.get("mark_seen") == False, "mark_seen must be False!"
        assert results[0]["message_id"] == "<unique-123@test.com>", "Should use Message-ID, not UID!"
        print("[PASS] Mail Source: Uses mark_seen=False and proper Message-ID.")

    # 2. Test Processor Safe Fallback & Versioning
    test_dir = Path(__file__).resolve().parent.parent / "test_data_p3"
    mock_db = DatabaseManager(base_dir=test_dir)
    
    mock_source = MagicMock()
    mock_source.fetch_recent.return_value = [{
        "message_id": "<msg-002>",
        "received_at": "2026-10-12T10:00:00",
        "sender": "test@test.com",
        "subject": "Plain Text Only",
        "html_body": "",
        "text_body": "Hello & <script>alert(1)</script>"
    }]
    
    processor = EmailProcessor(mail_source=mock_source, db=mock_db)
    stats = processor.process_inbox(limit=5)
    
    assert stats["processed"] == 1, "Should process 1 email"
    
    # Verify the safe text is stored as pure, literal text (which is safe because 
    # the frontend uses textContent, not innerHTML) and versioned.
    safe_email = mock_db.get_safe_email("<msg-002>")
    assert "<script>" in safe_email["clean_body"], "Plain text should be stored as literal text."
    assert safe_email["rules_version"] == RULES_VERSION, "Rules version must be tracked!"
    print("[PASS] Processor: Plain text is safely stored as literal text and versioned.")

    print("\n=== All Phase 3 Mail & Storage Tests Passed! ===")

if __name__ == "__main__":
    test_phase3()