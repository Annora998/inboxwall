"""InBox Wall v2 - Command Line Interface."""
import sys
import subprocess
from pathlib import Path

def serve():
    """Start the Safe Mail Server and Dashboard."""
    import uvicorn
    print("Starting InBox Wall Safe Mail Server...")
    print("Dashboard: http://127.0.0.1:8000")
    print("API Token will be printed below (keep it secret)\n")
    uvicorn.run("inboxwall.ai_plug.safe_mail_server:app", host="127.0.0.1", port=8000, reload=False)

def run_mcp():
    """Start the MCP Server for AI integration."""
    from inboxwall.ai_plug.mcp_server import mcp
    print("Starting InBox Wall MCP Server...")
    print("AI tools can now connect via Model Context Protocol\n")
    mcp.run()

def sync():
    """Sync emails using credentials from the OS keychain."""
    import getpass
    from inboxwall.store.keychain import get_profile, save_profile
    from inboxwall.mail.mail_source import ImapMailSource
    from inboxwall.store.database import DatabaseManager
    from inboxwall.processor import EmailProcessor

    profile_name = "default"
    creds = get_profile(profile_name)

    if not creds:
        print(f"No credentials found for profile '{profile_name}' in OS keychain.")
        print("Please enter your IMAP details (they will be saved securely):\n")
        host = input("IMAP Host (e.g., imap.gmail.com): ").strip()
        port_str = input("IMAP Port (e.g., 993): ").strip()
        port = int(port_str) if port_str.isdigit() else 993
        username = input("Username/Email: ").strip()
        password = getpass.getpass("Password/App Password: ")
        
        save_profile(profile_name, host, port, username, password)
        print(f"\nCredentials saved securely to OS keychain as '{profile_name}'.\n")
        creds = get_profile(profile_name)

    print(f"Syncing using profile '{profile_name}' ({creds['username']})...")
    source = ImapMailSource(creds["host"], creds["port"], creds["username"], creds["password"])
    db = DatabaseManager()
    processor = EmailProcessor(mail_source=source, db=db)
    processor.process_inbox(limit=50)
    print("Sync complete.")

def doctor():
    """Check system health and configuration."""
    print("InBox Wall Doctor - System Health Check\n")
    print(f"Python Version: {sys.version.split()[0]}")
    
    required = [
        ("bs4", "beautifulsoup4"), ("lxml", "lxml"), ("css_inline", "css-inline"),
        ("imap_tools", "imap-tools"), ("fastapi", "fastapi"), ("uvicorn", "uvicorn"), 
        ("mcp", "mcp"), ("keyring", "keyring")
    ]
    missing = []
    for import_name, display_name in required:
        try:
            __import__(import_name)
            print(f"[OK] {display_name} installed")
        except ImportError:
            print(f"[FAIL] {display_name} MISSING")
            missing.append(display_name)
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}\nRun: pip install -e .")
        return
    
    from inboxwall.store.database import DatabaseManager
    db = DatabaseManager()
    print(f"[OK] Safe DB: {db.safe_db_path}")
    print(f"[OK] Vault DB: {db.vault_db_path}")
    
    print("\nAPI Token (for dashboard access):")
    from inboxwall.ai_plug.safe_mail_server import API_TOKEN
    print(f"   {API_TOKEN}")
    print("\nAll systems operational. Run 'inboxwall-serve' to start.")

def benchmark():
    """Run the pytest benchmark suite."""
    print("Running InBox Wall Benchmark...\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_benchmark.py", "-v", "-s"],
        cwd=Path(__file__).parent.parent
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  inboxwall-serve      Start the dashboard server")
        print("  inboxwall-mcp        Start the MCP server for AI")
        print("  inboxwall-sync       Securely sync emails using OS keychain")
        print("  inboxwall-doctor     Check system health")
        print("  inboxwall-benchmark  Run the test benchmark")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "serve": serve()
    elif command == "mcp": run_mcp()
    elif command == "sync": sync()
    elif command == "doctor": doctor()
    elif command == "benchmark": benchmark()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)