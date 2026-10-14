"""InBox Wall v2 - Safe Mail Server."""
import json
import secrets
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from inboxwall.store.database import DatabaseManager
from inboxwall.store.audit import AuditLogger
from inboxwall.engine.labels import label_for, intent_for, chip_for, breakdown_text, render_invisible

app = FastAPI(title="InBox Wall Safe Mail API", version="2.3.0")
API_TOKEN = secrets.token_urlsafe(32)
print(f"\n[SECURITY] API Token generated: {API_TOKEN}\n")

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
db = DatabaseManager()
audit = AuditLogger()


class ReviewAction(BaseModel):
    action: str


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
            "SELECT id, message_id, received_at, sender, subject, verdict, account FROM safe_emails ORDER BY received_at DESC LIMIT ?",
            (safe_limit,)
        )
        rows = [dict(r) for r in cursor.fetchall()]

    ids = [r["id"] for r in rows]
    kinds_map = {}
    if ids:
        with db._get_connection(db.vault_db_path, read_only=True) as conn:
            q = ",".join("?" * len(ids))
            cursor = conn.execute(
                f"SELECT safe_email_id, finding_kind FROM threat_vault WHERE safe_email_id IN ({q})",
                ids
            )
            for r in cursor.fetchall():
                kinds_map.setdefault(r["safe_email_id"], []).append(r["finding_kind"])

    for d in rows:
        kinds = kinds_map.get(d["id"], [])
        d["reason"] = chip_for(d["verdict"], kinds)
        d["is_demo"] = str(d.get("account", "")).endswith("@inboxwall.local")
    return rows


@app.get("/api/stats")
def stats(_: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    with db._get_connection(db.vault_db_path, read_only=True) as conn:
        cursor = conn.execute(
            "SELECT finding_kind, full_text FROM threat_vault WHERE recorded_at >= datetime('now', '-7 day')"
        )
        rows = [dict(r) for r in cursor.fetchall()]
    by_intent = {}
    for r in rows:
        intent = intent_for(r["finding_kind"], r["full_text"])
        by_intent[intent] = by_intent.get(intent, 0) + 1
    sync = db.get_sync()
    return {
        "blocked_week": len(rows),
        "by_intent": by_intent,
        "last_sync": sync.get("last_sync"),
        "mailbox": sync.get("mailbox"),
    }


@app.get("/api/emails/{safe_email_id}")
def get_email(safe_email_id: int, include_threats: bool = False, _: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    email = db.get_safe_email(safe_email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
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
        for t in threats:
            t["label"] = label_for(t["finding_kind"])
        orig = db.get_original(safe_email_id)
        original_html = orig["original_html"] if orig else ""

    score = email["threat_score"] or 0
    return {
        "id": email["id"],
        "message_id": email["message_id"],
        "sender": email["sender"],
        "subject": email["subject"],
        "received_at": email["received_at"],
        "rules_version": email["rules_version"],
        "threat_score": score,
        "score_explanation": breakdown_text(threats, score, email["verdict"]),
        "review_status": email["review_status"],
        "account": email["account"],
        "is_demo": str(email["account"]).endswith("@inboxwall.local"),
        "clean_body": email["clean_body"],
        "verdict": email["verdict"],
        "original_html": original_html,
        "original_xray": render_invisible(original_html),
        "threats": threats,
    }


@app.post("/api/emails/{safe_email_id}/review")
def review_email(safe_email_id: int, body: ReviewAction, _: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    email = db.get_safe_email(safe_email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if body.action == "keep_locked":
        db.set_review_status(safe_email_id, "locked")
        audit.log("human", "review_keep_locked", safe_email_id, email["message_id"], "ok")
        return {"status": "locked"}

    if body.action == "release":
        db.set_review_status(safe_email_id, "released", verdict="RELEASED")
        audit.log("human", "review_release", safe_email_id, email["message_id"], "ok")
        return {"status": "released"}

    if body.action == "report_false_positive":
        db.reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = db.reports_dir / f"false-positive-{safe_email_id}-{stamp}.json"
        orig = db.get_original(safe_email_id)
        payload = {
            "message_id": email["message_id"],
            "sender": email["sender"],
            "subject": email["subject"],
            "verdict": email["verdict"],
            "threat_score": email["threat_score"],
            "rules_version": email["rules_version"],
            "clean_body": email["clean_body"],
            "original_html": (orig or {}).get("original_html", "")[:50_000],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        db.set_review_status(safe_email_id, "reported")
        audit.log("human", "review_report_false_positive", safe_email_id, email["message_id"], "ok")
        return {"status": "reported", "file": str(path)}

    raise HTTPException(status_code=400, detail="Unknown action")


@app.post("/api/emails/{safe_email_id}/delete_original")
def delete_original(safe_email_id: int, _: bool = Depends(verify_token), request: Request = None):
    verify_host(request)
    db.delete_original(safe_email_id)
    audit.log("human", "delete_original", safe_email_id, None, "ok")
    return {"status": "deleted"}