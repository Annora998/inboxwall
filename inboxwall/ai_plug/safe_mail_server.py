"""InBox Wall v2 - Safe Mail Server."""
import secrets
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from inboxwall.store.database import DatabaseManager

app = FastAPI(title="InBox Wall Safe Mail API", version="2.2.0")
API_TOKEN = secrets.token_urlsafe(32)
print(f"\n[SECURITY] API Token generated: {API_TOKEN}\n")

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
db = DatabaseManager()

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if not secrets.compare_digest(authorization.split(" ")[1], API_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid token")
    return True

def verify_host(request: Request):
    host = request.headers.get("host", "")
    if host not in ["127.0.0.1:8000", "localhost:8000"]:
        raise HTTPException(status_code=403, detail="Invalid host")

@app.get("/", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    verify_host(request)
    dashboard_path = FRONTEND_DIR / "dashboard.html"
    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8").replace("{{API_TOKEN}}", API_TOKEN)
    return "<h1>Dashboard not found.</h1>"

@app.get("/api/emails")
def list_emails(limit: int = 50, _: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    safe_limit = max(1, min(limit, 100))
    with db._get_connection(db.safe_db_path, read_only=True) as conn:
        cursor = conn.execute(
            "SELECT id, message_id, received_at, sender, subject, verdict FROM safe_emails ORDER BY received_at DESC LIMIT ?",
            (safe_limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

@app.get("/api/emails/{safe_email_id}")
def get_email(safe_email_id: int, include_threats: bool = False, _: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    email = db.get_safe_email(safe_email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    # AI-facing calls (no include_threats) can never open locked mail.
    # The human dashboard (include_threats=true) may audit it.
    if email["verdict"] == "LOCKED_AWAY" and not include_threats:
        raise HTTPException(status_code=403, detail="This email is locked due to high threat score")

    threats = []
    original_html = ""
    if include_threats:
        with db._get_connection(db.vault_db_path, read_only=True) as conn:
            cursor = conn.execute(
                "SELECT finding_kind, full_text, position FROM threat_vault WHERE safe_email_id = ?",
                (safe_email_id,)
            )
            threats = [dict(row) for row in cursor.fetchall()]
        orig = db.get_original(safe_email_id)
        original_html = orig["original_html"] if orig else ""

    return {
        "id": email["id"],
        "message_id": email["message_id"],
        "sender": email["sender"],
        "subject": email["subject"],
        "received_at": email["received_at"],
        "rules_version": email["rules_version"],
        "threat_score": email["threat_score"],
        "clean_body": email["clean_body"],
        "verdict": email["verdict"],
        "original_html": original_html,
        "threats": threats,
    }