"""InBox Wall v2 - Engine Pipeline (metadata scanning)."""
from inboxwall.engine.models import Verdict, WEIGHTS, Finding
from inboxwall.engine.sanitizer import Sanitizer
from inboxwall.engine.cheap_cut.invisible_chars import InvisibleCharScanner
from inboxwall.engine.cheap_cut.phrase_scanner import PhraseScanner
from inboxwall.engine.style_utils import normalize_text

MAX_HTML_SIZE = 5 * 1024 * 1024
MAX_METADATA_SIZE = 500

class WallPipeline:
    def __init__(self):
        self.sanitizer = Sanitizer()
        self.invisible_scanner = InvisibleCharScanner()
        self.phrase_scanner = PhraseScanner()

    def scan_metadata(self, text: str) -> tuple:
        """Strip invisible chars, cap length, and scan metadata with the same engine."""
        if not isinstance(text, str):
            return "", []
        cleaned = self.invisible_scanner.strip_safe(text)[:MAX_METADATA_SIZE]
        if not cleaned.strip():
            return "", []
        findings = []
        norm = normalize_text(cleaned)
        if ("ignore" in norm or "disregard" in norm or "forget" in norm) and \
           ("previous" in norm or "above" in norm or "prior" in norm) and \
           ("instruction" in norm or "rule" in norm):
            findings.append(Finding(kind="hidden_instruction", full_text=cleaned, position="metadata"))
        elif "system" in norm and "override" in norm:
            findings.append(Finding(kind="hidden_instruction", full_text=cleaned, position="metadata"))
        else:
            for f in self.phrase_scanner.scan(norm):
                findings.append(Finding(kind=f.kind, full_text=f.full_text, position="metadata"))
        return cleaned, findings

    def sanitize_metadata(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return self.invisible_scanner.strip_safe(text)

    def process(self, html: str, subject: str = "", sender: str = "") -> dict:
        safe_subject, subject_findings = self.scan_metadata(subject)
        safe_sender, sender_findings = self.scan_metadata(sender)
        metadata_findings = subject_findings + sender_findings

        clean_text = "[EMAIL BLOCKED DUE TO PROCESSING ERROR]"
        findings = []

        if not isinstance(html, str):
            findings.append(Finding(kind="scanner_crash", full_text="Invalid HTML input", fail_closed=True))
            return self._finish(findings + metadata_findings, clean_text, safe_subject, safe_sender)

        if len(html) > MAX_HTML_SIZE:
            findings.append(Finding(kind="oversized_html", full_text="File too large", fail_closed=True))
            return self._finish(findings + metadata_findings, clean_text, safe_subject, safe_sender)

        try:
            clean_text, sanitizer_findings = self.sanitizer.clean(html)
            findings.extend(sanitizer_findings)
            norm_text = normalize_text(clean_text)

            for f in self.invisible_scanner.scan(html):
                findings.append(Finding(
                    kind="tag_chars" if "E0000" in f["range"] else "zero_width_in_word",
                    full_text=f"Found {f['count']} chars in {f['range']}",
                    position="raw_html"
                ))
            findings.extend(self.phrase_scanner.scan(norm_text))
        except Exception as e:
            findings.append(Finding(kind="scanner_crash", full_text=str(e), fail_closed=True))
            clean_text = "[EMAIL BLOCKED DUE TO PROCESSING ERROR]"

        return self._finish(findings + metadata_findings, clean_text, safe_subject, safe_sender)

    def _finish(self, findings, clean_text, safe_subject, safe_sender):
        result = self._build_result(findings, clean_text)
        result["safe_subject"] = safe_subject
        result["safe_sender"] = safe_sender
        return result

    def _build_result(self, findings: list, clean_text: str) -> dict:
        if any(f.fail_closed for f in findings):
            verdict, score = Verdict.LOCKED_AWAY, 100
        else:
            score = sum(f.weight for f in findings)
            if score >= 10:
                verdict = Verdict.LOCKED_AWAY
                clean_text = "[EMAIL LOCKED AWAY DUE TO HIGH THREAT SCORE]"
            elif score > 0:
                verdict = Verdict.CLEANED
            else:
                verdict = Verdict.CLEAN
        return {"verdict": verdict, "score": score, "findings": findings, "clean_text": clean_text}