"""InBox Wall v2 - Invisible Character Scanner."""
import re

class InvisibleCharScanner:
    INVISIBLE_RANGES = [(0x200B, 0x200B), (0x200E, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0xFEFF, 0xFEFF), (0xE0000, 0xE007F)]

    def scan(self, text: str) -> list:
        findings = []
        for start, end in self.INVISIBLE_RANGES:
            rng = f"U+{start:04X}-U+{end:04X}"
            matches = list(re.finditer(f"[{chr(start)}-{chr(end)}]", text))
            if not matches:
                continue
            count = len(matches)
            first = matches[0]
            ctx = text[max(0, first.start() - 20):min(len(text), first.end() + 20)]
            ctx = re.sub(r"\s+", " ", ctx).strip()
            noun = "character" if count == 1 else "characters"
            findings.append({
                "type": "invisible_char",
                "count": count,
                "range": rng,
                "summary": f"{count} invisible {noun} ({rng}) inside: \"{ctx}\"",
            })
        return findings

    def strip_safe(self, text: str) -> str:
        # FIX: Added variation selectors, soft hyphen, braille blank, hangul fillers, and LRM/RLM to strip list
        text = re.sub(r"[\U000E0000-\U000E007F\uFE00-\uFE0F\u00AD\u2800\u3164\uFFA0\u200E\u200F]", "", text)
        text = re.sub(r"[\u202A-\u202E\u2066-\u2069]", "", text)
        text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u2060", "")
        text = re.sub(r"([a-zA-Z])[\u200c\u200d]+([a-zA-Z])", r"\1\2", text)
        text = re.sub(r"[\u200c\u200d]{4,}", "", text)
        return text