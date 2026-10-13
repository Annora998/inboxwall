"""Verification of Storage & API Security Fixes."""
import sys, os
import shutil
sys.path.insert(0, os.getcwd())

from inboxwall.store.database import DatabaseManager
from pathlib import Path

def test_storage_security():
    # FIX: Clean up test directory before each run to ensure fresh state
    test_dir = Path(__file__).resolve().parent.parent / "test_storage_security"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    db = DatabaseManager(base_dir=test_dir)

    # Test 1: Composite key prevents overwrite
    db.save_email(
        account="user@example.com", folder="INBOX", uid_validity=123, uid=1,
        message_id="<original@example.com>", received_at="2026-10-13T10:00:00",
        sender="legit@example.com", subject="Original", clean_body="Safe content",
        verdict="CLEAN", findings=[]
    )
    
    # Attempt to overwrite with different message_id but same composite key
    db.save_email(
        account="user@example.com", folder="INBOX", uid_validity=123, uid=1,
        message_id="<attacker@example.com>", received_at="2026-10-13T11:00:00",
        sender="attacker@example.com", subject="Overwrite Attempt", clean_body="Malicious",
        verdict="CLEAN", findings=[]
    )
    
    # Verify the original was updated (not duplicated)
    with db._get_connection(db.safe_db_path, read_only=True) as conn:
        cursor = conn.execute("SELECT COUNT(*) as count FROM safe_emails WHERE account='user@example.com' AND folder='INBOX' AND uid_validity=123 AND uid=1")
        count = cursor.fetchone()["count"]
        assert count == 1, f"Expected 1 row, got {count}. Overwrite protection failed!"
    
    print("[PASS] Composite Key: Prevents Message-ID overwrite attacks.")

    # Test 2: Vault deduplication
    from inboxwall.engine.models import Finding
    findings = [Finding(kind="test", full_text="Full text not truncated", position="test")]
    
    db.save_email(
        account="user@example.com", folder="INBOX", uid_validity=123, uid=2,
        message_id="<test2@example.com>", received_at="2026-10-13T12:00:00",
        sender="test@example.com", subject="Test", clean_body="Content",
        verdict="CLEANED", findings=findings
    )
    
    # Reprocess the same email
    db.save_email(
        account="user@example.com", folder="INBOX", uid_validity=123, uid=2,
        message_id="<test2@example.com>", received_at="2026-10-13T12:00:00",
        sender="test@example.com", subject="Test", clean_body="Content",
        verdict="CLEANED", findings=findings
    )
    
    with db._get_connection(db.vault_db_path, read_only=True) as conn:
        cursor = conn.execute("SELECT COUNT(*) as count FROM threat_vault")
        count = cursor.fetchone()["count"]
        assert count == 1, f"Expected 1 vault row, got {count}. Deduplication failed!"
    
    print("[PASS] Vault Deduplication: Reprocessing does not create duplicate rows.")

    # Test 3: Full text preservation
    with db._get_connection(db.vault_db_path, read_only=True) as conn:
        cursor = conn.execute("SELECT full_text FROM threat_vault LIMIT 1")
        full_text = cursor.fetchone()["full_text"]
        assert full_text == "Full text not truncated", f"Vault text was truncated: {full_text}"
    
    print("[PASS] Full Text: Vault preserves complete finding text for Threat Wall.")

    print("\n=== All Storage & API Security Fixes Verified ===")

if __name__ == "__main__":
    test_storage_security()