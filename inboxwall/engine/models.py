"""InBox Wall v2 - Central Models."""
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Verdict(str, Enum):
    CLEAN = "CLEAN"
    CLEANED = "CLEANED"
    LOCKED_AWAY = "LOCKED_AWAY"
    RELEASED = "RELEASED"

WEIGHTS = {
    "hidden_instruction": 10, "tag_chars": 10, "hidden_block_large": 6,
    "zero_width_in_word": 4, "visible_phrase": 3, "hidden_preheader": 0,
    "oversized_html": 100, "scanner_crash": 100, "bidi_control": 8,
    "white_on_white": 5, "transparent_text": 5, "tiny_font": 4,
    "offscreen": 5, "opacity_zero": 5, "clipped_box": 5, "mso_hide": 3,
    "display_none": 0, "visibility_hidden": 0,
}

@dataclass
class Finding:
    kind: str
    full_text: str
    position: Optional[str] = None
    fail_closed: bool = False

    @property
    def weight(self) -> int:
        return WEIGHTS.get(self.kind, 0)