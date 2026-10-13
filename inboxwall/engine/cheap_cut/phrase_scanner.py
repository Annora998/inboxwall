"""InBox Wall v2 - Phrase Scanner.

Spots fake system labels and known attack phrases in normalized text.
"""
import re
from inboxwall.engine.models import Finding

class PhraseScanner:
    """Scans normalized text for known prompt injection phrases."""

    DANGEROUS_PHRASES = [
        r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|rules)",
        r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|rules)",
        r"system\s+override",
        r"reply\s+with\s+(your\s+)?password",
        r"forward\s+(all\s+)?(emails?|mail)\s+to\s+@",
    ]

    def __init__(self):
        self._rules = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PHRASES]

    def scan(self, text: str) -> list:
        """Return Finding objects for every dangerous phrase found."""
        findings = []
        for rule in self._rules:
            match = rule.search(text)
            if match:
                findings.append(Finding(
                    kind="visible_phrase",
                    full_text=match.group(0),
                    position="normalized_body"
                ))
        return findings