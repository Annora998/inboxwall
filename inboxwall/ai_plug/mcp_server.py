"""InBox Wall v2 - MCP (Model Context Protocol) Server.

This is the official plug for AI tools. It exposes our Safe Copy database
as native "Tools" that AI agents can call securely.
"""
import json
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from inboxwall.store.database import DatabaseManager

# Initialize the MCP server
mcp = FastMCP("InBox Wall Safe Mail")

# Point to the main data folder

db = DatabaseManager(read_only=True)

@mcp.tool()
def list_protected_emails(limit: int = 10) -> str:
    with db._get_connection(db.safe_db_path, read_only=True) as conn:
        # FIX: Filter out LOCKED_AWAY emails. AI should never see them, not even their subjects.
        cursor = conn.execute(
            "SELECT id, message_id, sender, subject, verdict FROM safe_emails WHERE verdict != 'LOCKED_AWAY' ORDER BY received_at DESC LIMIT ?", 
            (limit,)
        )
        return json.dumps([dict(row) for row in cursor.fetchall()], indent=2)

@mcp.tool()
def read_safe_email(safe_email_id: int) -> str:
    email = db.get_safe_email(safe_email_id)
    if not email:
        return json.dumps({"error": "Email not found in Safe Copy"})
    
    # FIX: Never show locked mail to AI
    if email["verdict"] == "LOCKED_AWAY":
        return json.dumps({"error": "This email is locked due to high threat score"})
    
    return json.dumps({"sender": email["sender"], "subject": email["subject"], "clean_body": email["clean_body"], "verdict": email["verdict"]}, indent=2)

# This allows the server to run standalone
if __name__ == "__main__":
    mcp.run()