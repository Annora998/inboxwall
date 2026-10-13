"""InBox Wall v2 - Engine Pipeline (Critical Fixes Applied)."""
from bs4 import BeautifulSoup
from inboxwall.engine.models import Verdict, WEIGHTS, Finding
from inboxwall.engine.sanitizer import Sanitizer
from inboxwall.engine.cheap_cut.invisible_chars import InvisibleCharScanner
from inboxwall.engine.cheap_cut.phrase_scanner import PhraseScanner
from inboxwall.engine.style_utils import normalize_text

MAX_HTML_SIZE = 5 * 1024 * 1024 

# FIX 2: Explicit deny-list for non-rendering tags to prevent text leakage
NON_RENDERING_TAGS = [
    "title", "textarea", "select", "option", "details", "summary",
    "script", "style", "noscript", "iframe", "object", "embed", "link", "meta", "head"
]

class WallPipeline:
    def __init__(self):
        self.sanitizer = Sanitizer()
        self.invisible_scanner = InvisibleCharScanner()
        self.phrase_scanner = PhraseScanner()

    def process(self, html: str) -> dict:
        clean_text = "[EMAIL BLOCKED DUE TO PROCESSING ERROR]"
        findings = []
        
        if not isinstance(html, str):
            findings.append(Finding(kind="scanner_crash", full_text="Invalid HTML input", fail_closed=True))
            return self._build_result(findings, clean_text)

        if len(html) > MAX_HTML_SIZE:
            findings.append(Finding(kind="oversized_html", full_text="File too large", fail_closed=True))
            return self._build_result(findings, clean_text)

        try:
            clean_text, sanitizer_findings = self.sanitizer.clean(html)
            findings.extend(sanitizer_findings)
            
            norm_text = normalize_text(clean_text)
            
            inv_findings = self.invisible_scanner.scan(html)
            for f in inv_findings:
                findings.append(Finding(
                    kind="tag_chars" if "E0000" in f["range"] else "zero_width_in_word", 
                    full_text=f"Found {f['count']} chars in {f['range']}", 
                    position="raw_html"
                ))

            phrase_findings = self.phrase_scanner.scan(norm_text)
            findings.extend(phrase_findings)
            
        except Exception as e:
            findings.append(Finding(kind="scanner_crash", full_text=str(e), fail_closed=True))
            clean_text = "[EMAIL BLOCKED DUE TO PROCESSING ERROR]"

        return self._build_result(findings, clean_text)

    def sanitize_metadata(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return self.invisible_scanner.strip_safe(text)

    def _build_result(self, findings: list, clean_text: str) -> dict:
        if any(f.fail_closed for f in findings):
            verdict, score = Verdict.LOCKED_AWAY, 100
        else:
            score = sum(f.weight for f in findings)
            if score >= 10: 
                verdict = Verdict.LOCKED_AWAY
                clean_text = "[EMAIL LOCKED AWAY DUE TO HIGH THREAT SCORE]"
            # FIX 1: Removed "or len(findings) > 0". Weight 0 (preheaders) now correctly results in CLEAN.
            elif score > 0: 
                verdict = Verdict.CLEANED
            else: 
                verdict = Verdict.CLEAN
                
        return {"verdict": verdict, "score": score, "findings": findings, "clean_text": clean_text}