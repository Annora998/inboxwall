"""Professional Test Suite for the MCP Server."""
import sys
import os

# Ensure we can import the server
sys.path.insert(0, os.getcwd())

from inboxwall.ai_plug.mcp_server import mcp

def test_mcp_server():
    # 1. Verify Server Name
    assert mcp.name == "InBox Wall Safe Mail", "Server name mismatch"
    print("[PASS] MCP: Server initialized with correct name.")

    # 2. Verify Tools are Registered
    # FastMCP stores tools in its internal registry
    tool_names = list(mcp._tool_manager._tools.keys())
    
    assert "list_protected_emails" in tool_names, "Missing list tool!"
    assert "read_safe_email" in tool_names, "Missing read tool!"
    print(f"[PASS] MCP: Tools registered successfully: {tool_names}")

    print("\n=== MCP Server is Ready for AI Integration! ===")

if __name__ == "__main__":
    test_mcp_server()