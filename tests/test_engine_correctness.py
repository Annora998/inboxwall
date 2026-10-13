"""Verification of Engine Correctness Fixes."""
import sys, os
sys.path.insert(0, os.getcwd())

from inboxwall.engine.sanitizer import Sanitizer
from inboxwall.engine.style_utils import hidden_reason, parse_style
from inboxwall.engine.cheap_cut.invisible_chars import InvisibleCharScanner

def test_engine_correctness():
    sanitizer = Sanitizer()
    scanner = InvisibleCharScanner()

    # FIX A: font-size:0 wrapper should NOT wipe a child with font-size:16px
    html_wrapper = "<div style='font-size:0px;'><span style='font-size:16px;'>Your order has shipped.</span></div>"
    clean_text, findings = sanitizer.clean(html_wrapper)
    
    assert "Your order has shipped" in clean_text, f"Wrapper wipe bug! Clean text: {clean_text}"
    print("[PASS] Wrapper Inheritance: Child with valid font-size is preserved.")

    # FIX B: White text on unknown/dark background should NOT be flagged
    style_dark = parse_style("color: #ffffff; background-color: #000000;")
    assert hidden_reason(style_dark) != "white_on_white", "Should not flag white on black"
    
    style_unknown = parse_style("color: #ffffff;")
    assert hidden_reason(style_unknown) != "white_on_white", "Should not flag white on unknown background"
    
    style_explicit_white = parse_style("color: #ffffff; background-color: #ffffff;")
    assert hidden_reason(style_explicit_white) == "white_on_white", "Should flag explicit white on white"
    print("[PASS] White-on-White: Only flags when background is explicitly light.")

    # FIX C: Malayalam/Arabic joiners should be preserved, Latin injection stripped
    malayalam_text = "ക\u200dൂട്ട്" # Legitimate Malayalam conjunct with ZWJ
    clean_malayalam = scanner.strip_safe(malayalam_text)
    assert "\u200d" in clean_malayalam, "Legitimate Malayalam ZWJ was corrupted!"
    
    attack_text = "Ig\u200dnore" # Latin word with ZWJ injection
    clean_attack = scanner.strip_safe(attack_text)
    assert "\u200d" not in clean_attack, "Latin ZWJ injection was not stripped!"
    assert clean_attack == "Ignore", f"Expected 'Ignore', got '{clean_attack}'"
    print("[PASS] Joiner Policy: Legitimate script joiners preserved, Latin injections stripped.")

    print("\n=== All Engine Correctness Fixes Verified ===")

if __name__ == "__main__":
    test_engine_correctness()