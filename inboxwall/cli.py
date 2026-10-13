"""InBox Wall v2 - Command Line Interface."""
import sys
import subprocess
from pathlib import Path

def serve():
    """Start the Safe Mail Server and Dashboard."""
    import uvicorn
    print("🛡️  Starting InBox Wall Safe Mail Server...")
    print("📍 Dashboard: http://127.0.0.1:8000")
    print("🔒 API Token will be printed below (keep it secret)\n")
    uvicorn.run("inboxwall.ai_plug.safe_mail_server:app", host="127.0.0.1", port=8000, reload=False)

def run_mcp():
    """Start the MCP Server for AI integration."""
    from inboxwall.ai_plug.mcp_server import mcp
    print("🤖 Starting InBox Wall MCP Server...")
    print("📡 AI tools can now connect via Model Context Protocol\n")
    mcp.run()

def doctor():
    """Check system health and configuration."""
    print("🩺 InBox Wall Doctor - System Health Check\n")
    
    # Check Python version
    print(f"✓ Python Version: {sys.version.split()[0]}")
    
    # FIX: Use actual import names, not PyPI package names
    # Format: (import_name, display_name)
    required = [
        ("bs4", "beautifulsoup4"),
        ("lxml", "lxml"),
        ("css_inline", "css-inline"),
        ("imap_tools", "imap-tools"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("mcp", "mcp")
    ]
    
    missing = []
    for import_name, display_name in required:
        try:
            __import__(import_name)
            print(f"✓ {display_name} installed")
        except ImportError:
            print(f"✗ {display_name} MISSING")
            missing.append(display_name)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("   Run: pip install -e .")
        return
    
    # Check database
    from inboxwall.store.database import DatabaseManager
    db = DatabaseManager()
    print(f"✓ Safe DB: {db.safe_db_path}")
    print(f"✓ Vault DB: {db.vault_db_path}")
    
    # Check API token
    print("\n🔒 API Token (for dashboard access):")
    from inboxwall.ai_plug.safe_mail_server import API_TOKEN
    print(f"   {API_TOKEN}")
    
    print("\n✅ All systems operational. Run 'inboxwall-serve' to start.")

def benchmark():
    """Run the pytest benchmark suite."""
    print("🧪 Running InBox Wall Benchmark...\n")
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
        print("  inboxwall-doctor     Check system health")
        print("  inboxwall-benchmark  Run the test benchmark")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "serve":
        serve()
    elif command == "mcp":
        run_mcp()
    elif command == "doctor":
        doctor()
    elif command == "benchmark":
        benchmark()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)