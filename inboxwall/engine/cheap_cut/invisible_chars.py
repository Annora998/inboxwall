"""InBox Wall v2 - Invisible Character Scanner (Joiner Fix)."""
import re

class InvisibleCharScanner:
    # FIX: Removed 0x200C (ZWNJ) and 0x200D (ZWJ) from flagging ranges.
    # They are legitimate in Malayalam/Arabic/Hindi.
    INVISIBLE_RANGES = [
        (0x200B, 0x200B), # ZWSP
        (0x200E, 0x200F), # LRM, RLM
        (0x202A, 0x202E), # Bidi controls
        (0x2060, 0x206F), # Word joiner, invisible operators
        (0xFEFF, 0xFEFF), # BOM
        (0xE0000, 0xE007F) # Tag characters
    ]
    
    def scan(self, text: str) -> list:
        findings = []
        for start, end in self.INVISIBLE_RANGES:
            pattern = f"[{chr(start)}-{chr(end)}]"
            matches = re.findall(pattern, text)
            if matches:
                findings.append({"type": "invisible_char", "count": len(matches), "range": f"U+{start:04X}-U+{end:04X}"})
        return findings
        
    def strip_safe(self, text: str) -> str:
        # 1. Strip Tag characters entirely
        text = re.sub(r"[\U000E0000-\U000E007F]", "", text)
        # 2. Strip Bidi overrides
        text = re.sub(r"[\u202A-\u202E\u2066-\u2069]", "", text)
        # 3. Strip zero-width spaces, BOM, word joiners
        text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u2060", "")
        
        # 4. FIX: Only strip ZWNJ/ZWJ if they are inside Latin words or in long runs (>3)
        # Strip ZWJ/ZWNJ surrounded by ASCII letters (e.g., "a\u200db" -> "ab")
        text = re.sub(r"([a-zA-Z])[\u200c\u200d]+([a-zA-Z])", r"\1\2", text)
        # Strip long runs of ZWJ/ZWNJ (e.g., "\u200d\u200d\u200d\u200d")
        text = re.sub(r"[\u200c\u200d]{4,}", "", text)
        
        return text