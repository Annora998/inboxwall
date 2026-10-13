"""InBox Wall v2 - Central Models.

Single source of truth for verdicts, weights, and findings.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Verdict(str, Enum):
    CLEAN = "CLEAN"
    CLEANED = "CLEANED"
    LOCKED_AWAY = "LOCKED_AWAY"

# Centralized weights. 
WEIGHTS = {
    "hidden_instruction": 7,
    "tag_chars": 10,
    "hidden_block_large": 6,
    "zero_width_in_word": 4,
    "visible_phrase": 3,
    "hidden_preheader": 0,
    "oversized_html": 100,
    "scanner_crash": 100,
    "bidi_control": 8,
    "white_on_white": 5
}

@dataclass
class Finding:
    """Holds full context for the Threat Wall. Weight is derived from KIND."""
    kind: str
    full_text: str
    position: Optional[str] = None 
    fail_closed: bool = False

    @property
    def weight(self) -> int:
        return WEIGHTS.get(self.kind, 0)