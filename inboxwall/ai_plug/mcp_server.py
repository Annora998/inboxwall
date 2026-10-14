"""InBox Wall v2 - MCP Server (audit-logged, envelope-wrapped)."""
import json
from mcp.server.fastmcp import FastMCP
from inboxwall.store.database import DatabaseManager
from inboxwall.store.audit import AuditLogger
from inboxwall.ai_plug.envelope import wrap_untrusted

mcp = FastMCP("InBox Wall Safe Mail")
db = DatabaseManager(read_only=True)
audit = AuditLogger()

@mcp.tool()
def list_protected_emails(limit: int = 10) -> str:
    safe_limit = max(1, min(limit, 100))
    with db._get_connection(db.safe_db_path, read_only=True) as conn:
        cursor = conn.execute(
            "SELECT id, message_id, sender, subject, verdict FROM safe_emails WHERE verdict != 'LOCKED_AWAY' ORDER BY received_at DESC LIMIT ?",
            (safe_limit,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
    audit.log(tool="mcp", action="list_protected_emails", outcome="ok")
    return json.dumps(rows, indent=2)

@mcp.tool()
def read_safe_email(safe_email_id: int) -> str:
    email = db.get_safe_email(safe_email_id)
    if not email:
        audit.log(tool="mcp", action="read_safe_email", safe_email_id=safe_email_id, outcome="not_found")
        return json.dumps({"error": "Email not found in Safe Copy"})
    if email["verdict"] == "LOCKED_AWAY":
        audit.log(tool="mcp", action="read_safe_email", safe_email_id=safe_email_id, message_id=email["message_id"], outcome="denied_locked")
        return json.dumps({"error": "This email is locked due to high threat score. A human must review it in the dashboard."})
    audit.log(tool="mcp", action="read_safe_email", safe_email_id=safe_email_id, message_id=email["message_id"], outcome="ok")
    wrapped = wrap_untrusted(email["sender"], email["subject"], email["clean_body"])
    return json.dumps({"sender": email["sender"], "subject": email["subject"], "clean_body": wrapped, "verdict": email["verdict"]}, indent=2)

if __name__ == "__main__":
    mcp.run()