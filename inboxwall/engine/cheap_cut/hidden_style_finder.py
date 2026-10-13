"""InBox Wall - Cheap Cut: Hidden Style Finder.

Detects HTML styled to be invisible to humans but readable by AI.
"""

import re
from bs4 import BeautifulSoup


class HiddenStyleFinder:
    """Scans raw email HTML for text hidden by CSS styles."""

    HIDDEN_PATTERNS = [
        r"display\s*:\s*none",
        r"visibility\s*:\s*hidden",
        r"opacity\s*:\s*0(\.0+)?\s*(;|\s*$)",
        r"font-size\s*:\s*(0|1)(\.\d+)?\s*(px|pt|em|rem)?\s*(;|\s*$)",
    ]

    def __init__(self):
        self._rules = [re.compile(p, re.IGNORECASE) for p in self.HIDDEN_PATTERNS]

    def scan(self, html: str) -> list:
        """Return a list of findings for hidden text blocks."""
        soup = BeautifulSoup(html, "lxml")
        findings = []
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            if any(rule.search(style) for rule in self._rules):
                hidden_text = tag.get_text(strip=True)
                if hidden_text:
                    findings.append({
                        "type": "hidden_style",
                        "tag": tag.name,
                        "style": style.strip(),
                        "hidden_text": hidden_text,
                    })
        return findings