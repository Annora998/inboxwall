"""InBox Wall v2 - Engine Sanitizer."""
import logging
import css_inline
from bs4 import BeautifulSoup, Comment
from inboxwall.engine.style_utils import parse_style, hidden_reason, classify_hidden, get_effective_style
from inboxwall.engine.cheap_cut.invisible_chars import InvisibleCharScanner
from inboxwall.engine.models import Finding

class Sanitizer:
    def __init__(self):
        self.invisible_scanner = InvisibleCharScanner()

    def clean(self, html: str) -> tuple[str, list]:
        findings = []

        # Inline all CSS so class-based hiding becomes detectable.
        try:
            html = css_inline.inline(
                html,
                keep_style_tags=False,
                keep_link_tags=False,
                load_remote_stylesheets=False
            )
        except Exception as e:
            # FAIL CLOSED: without inlining we cannot trust class-based hiding.
            return (
                "[EMAIL BLOCKED DUE TO CSS PROCESSING ERROR]",
                [Finding(kind="scanner_crash", full_text=f"CSS inlining failed: {e}", fail_closed=True)]
            )

        soup = BeautifulSoup(html, "lxml")

        non_rendering_tags = [
            "title", "textarea", "select", "option", "details", "summary",
            "script", "style", "noscript", "iframe", "object", "embed",
            "link", "meta", "head", "template"
        ]
        for tag in soup(non_rendering_tags):
            tag.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        for tag in soup.find_all(True):
            if tag.has_attr("hidden"):
                text_content = tag.get_text(separator=" ", strip=True)
                if text_content:
                    classification = classify_hidden(text_content)
                    findings.append(Finding(
                        kind=classification,
                        full_text=text_content,
                        position="hidden_attribute"
                    ))
                    tag.clear()
                    if classification == "hidden_instruction":
                        tag.append("[BLOCKED_POTENTIAL_INJECTION]")
                continue

            # Effective style accounts for inheritance (subtree hiders + cascade)
            style_dict = get_effective_style(tag)
            reason = hidden_reason(style_dict)

            if reason:
                text_content = tag.get_text(separator=" ", strip=True)
                if text_content:
                    classification = classify_hidden(text_content)
                    findings.append(Finding(
                        kind=classification,
                        full_text=text_content,
                        position=f"inline_style ({reason})"
                    ))

                    # Subtree hiders clear everything; soft hides only clear leaf nodes
                    hard_hides = {
                        "display_none", "visibility_hidden", "mso_hide",
                        "clipped_box", "offscreen", "opacity_zero"
                    }
                    child_tags = list(tag.find_all(recursive=False))
                    if reason in hard_hides or not child_tags:
                        tag.clear()
                        if classification == "hidden_instruction":
                            tag.append("[BLOCKED_POTENTIAL_INJECTION]")

        clean_text = soup.get_text(separator="\n", strip=True)
        clean_text = self.invisible_scanner.strip_safe(clean_text)
        return clean_text, findings