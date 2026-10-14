"""InBox Wall v2 - Human-readable labels, intents, chips, and X-ray rendering."""
import re

FINDING_LABELS = {
    "hidden_instruction": "Hidden instruction aimed at the AI",
    "hidden_block_large": "Large hidden text block",
    "hidden_preheader": "Hidden preview text (usually harmless)",
    "tag_chars": "Message hidden in Unicode tag characters",
    "zero_width_in_word": "Invisible character inside a word",
    "visible_phrase": "Suspicious instruction in visible text",
    "white_on_white": "White text on a white background",
    "transparent_text": "Fully transparent text",
    "bidi_control": "Text-direction override character",
    "tiny_font": "Extremely small font",
    "offscreen": "Text pushed off-screen",
    "opacity_zero": "Fully transparent block",
    "display_none": "Hidden block (display:none)",
    "visibility_hidden": "Hidden block (visibility)",
    "oversized_html": "Email too large to process safely",
    "scanner_crash": "Processing failed safely (fail-closed)",
}

def label_for(kind: str) -> str:
    return FINDING_LABELS.get(kind, kind.replace("_", " "))

def intent_for(kind: str, full_text: str) -> str:
    t = (full_text or "").lower()
    if ("forward" in t) and ("mail" in t or "email" in t):
        return "Mail forwarding"
    if "password" in t or "credential" in t:
        return "Data theft"
    if kind in ("hidden_instruction", "visible_phrase") or "ignore" in t or "override" in t:
        return "AI manipulation"
    if kind in ("zero_width_in_word", "tag_chars", "bidi_control"):
        return "Obfuscation"
    return "Hidden content"

def chip_for(verdict: str, kinds) -> str:
    kinds = [k for k in (kinds or []) if k]
    if verdict == "LOCKED_AWAY":
        if any(k in ("hidden_instruction", "visible_phrase") for k in kinds):
            return "Hidden AI instruction quarantined"
        return "High-risk content quarantined"
    if not kinds:
        return ""
    if kinds == ["hidden_preheader"]:
        return "Sender preview text ignored"
    n = len(kinds)
    return f"{n} hidden {'item' if n == 1 else 'items'} removed"

def score_breakdown(threats) -> list:
    from inboxwall.engine.models import WEIGHTS
    groups = {}
    for t in threats:
        kind = t["finding_kind"]
        w = WEIGHTS.get(kind, 0)
        g = groups.setdefault(kind, {"kind": kind, "label": label_for(kind), "weight_each": w, "count": 0})
        g["count"] += 1
    out = sorted(groups.values(), key=lambda g: -(g["weight_each"] * g["count"]))
    for g in out:
        g["total"] = g["weight_each"] * g["count"]
    return out

def breakdown_text(threats, score, verdict) -> str:
    parts = []
    for g in score_breakdown(threats):
        if g["total"] <= 0:
            continue
        cnt = f" x{g['count']}" if g["count"] > 1 else ""
        parts.append(f"{g['label']} ({g['weight_each']}{cnt})")
    if not parts:
        return "No weighted threats found."
    text = " + ".join(parts) + f" = {score}."
    if verdict == "LOCKED_AWAY":
        text += " Locked at 10 or above."
    return text

_INVISIBLE_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\U000E0000-\U000E007F]")

def render_invisible(text: str) -> str:
    """Replace invisible characters with visible tokens like U+200B in brackets."""
    if not text:
        return ""
    return _INVISIBLE_RE.sub(lambda m: f"\u27e6U+{ord(m.group(0)):04X}\u27e7", text)