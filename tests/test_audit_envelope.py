"""Tests for audit log and untrusted-content envelope."""
import sys, os, shutil
sys.path.insert(0, os.getcwd())

from pathlib import Path
from inboxwall.store.audit import AuditLogger
from inboxwall.ai_plug.envelope import wrap_untrusted

def test_audit_log_records_access():
    test_dir = Path(__file__).resolve().parent.parent / "test_audit_tmp"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    logger = AuditLogger(base_dir=test_dir)
    logger.log(tool="mcp", action="read_safe_email", safe_email_id=7, message_id="<m@x>", outcome="ok")
    logger.log(tool="mcp", action="read_safe_email", safe_email_id=8, outcome="denied_locked")
    rows = logger.recent(limit=10)
    assert len(rows) == 2
    assert rows[0]["outcome"] == "denied_locked"
    assert rows[1]["safe_email_id"] == 7
    assert rows[1]["accessed_at"]

def test_envelope_wraps_content():
    wrapped = wrap_untrusted("a@b.com", "Hello", "Body text")
    assert wrapped.startswith(ENVELOPE_HEADER)
    assert wrapped.endswith(ENVELOPE_FOOTER)
    assert "Body text" in wrapped
    assert "Sender: a@b.com" in wrapped