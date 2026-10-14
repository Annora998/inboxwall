"""InBox Wall v2 - Engine Sanitizer."""
import css_inline
from bs4 import BeautifulSoup, Comment, NavigableString
from inboxwall.engine.style_utils import parse_style, hidden_reason, classify_hidden, get_effective_style
from inboxwall.engine.cheap_cut.invisible_chars import InvisibleCharScanner
from inboxwall.engine.models import Finding

VISIBLE_TEXT_TAGS = {
    "[document]", "html", "body", "div", "p", "span", "a", "pre", "code",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption",
    "blockquote", "q", "cite", "em", "strong", "b", "i", "u", "s", "small",
    "big", "sub", "sup", "mark", "abbr", "time", "label", "button",
    "article", "section", "header", "footer", "main", "nav", "aside",
    "figure", "figcaption", "address", "center", "font", "ins", "del",
    "kbd", "samp", "var", "bdi", "bdo", "ruby", "rt", "rp", "hgroup",
}

def _extract_visible_text(soup) -> str:
    parts = []
    for text_node in soup.find_all(string=True):
        if type(text_node) is not NavigableString:
            continue
        parent = text_node.parent
        name = getattr(parent, "name", "[document]")
        if name in VISIBLE_TEXT_TAGS:
            chunk = str(text_node).strip()
            if chunk:
                parts.append(chunk)
    return "\n".join(parts)

class Sanitizer:
    def __init__(self):
        self.invisible_scanner = InvisibleCharScanner()

    def clean(self, html: str) -> tuple[str, list]:
        findings = []

        try:
            html = css_inline.inline(
                html,
                keep_style_tags=False,
                keep_link_tags=False,
                load_remote_stylesheets=False
            )
        except Exception as e:
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

            style_dict = get_effective_style(tag)
            reason = hidden_reason(style_dict)

            if reason:
                text_content = tag.get_text(separator=" ", strip=True)
                if text_content:
                    classification = classify_hidden(text_content)
                    if classification in ("hidden_instruction", "hidden_block_large"):
                        kind = classification
                    else:
                        kind = reason
                    findings.append(Finding(
                        kind=kind,
                        full_text=text_content,
                        position=f"inline_style ({reason})"
                    ))

                    hard_hides = {
                        "display_none", "visibility_hidden", "mso_hide",
                        "clipped_box", "offscreen", "opacity_zero"
                    }
                    if reason in hard_hides:
                        tag.clear()
                        if classification == "hidden_instruction":
                            tag.append("[BLOCKED_POTENTIAL_INJECTION]")
                    else:
                        # FIX: For soft hides, remove direct text nodes but leave child tags 
                        # to be evaluated independently by the loop.
                        for child in list(tag.children):
                            if isinstance(child, NavigableString):
                                child.extract()

        clean_text = _extract_visible_text(soup)
        clean_text = self.invisible_scanner.strip_safe(clean_text)
        return clean_text, findings