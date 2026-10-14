"""InBox Wall v2 - Shared Style Utilities."""
import re
import unicodedata

def parse_style(style_str: str) -> dict:
    out = {}
    if not style_str:
        return out
    style_str = re.sub(r"/\*.*?\*/", "", style_str)
    for part in style_str.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.replace("!important", "").strip().lower()
    return out

def get_effective_style(tag):
    effective = {}
    current = tag
    ancestors_styles = []

    while current is not None and getattr(current, "name", None):
        ancestors_styles.append(parse_style(current.get("style", "")))
        current = current.parent

    for style_dict in ancestors_styles:
        if style_dict.get("display") == "none":
            effective["display"] = "none"
        if style_dict.get("visibility") in ("hidden", "collapse"):
            effective["visibility"] = style_dict.get("visibility")
        if style_dict.get("mso-hide") == "all":
            effective["mso-hide"] = "all"
        try:
            op = float(style_dict.get("opacity", "1"))
            if op <= 0.05:
                effective["opacity"] = "0"
        except ValueError:
            pass

    for prop in ("color", "background-color", "font-size"):
        for style_dict in ancestors_styles:
            if prop in style_dict:
                effective[prop] = style_dict[prop]
                break

    for prop in ("position", "clip", "overflow", "height", "left", "top", "right", "bottom", "margin-left", "text-indent", "transform"):
        for style_dict in ancestors_styles:
            if prop in style_dict:
                effective[prop] = style_dict[prop]
                break

    return effective

def hidden_reason(style_dict: dict) -> str:
    if style_dict.get("display") == "none": return "display_none"
    if style_dict.get("visibility") in ("hidden", "collapse"): return "visibility_hidden"

    color = style_dict.get("color", "")
    bg_color = style_dict.get("background-color", "")

    if color == "transparent" or ("rgba" in color and ",0)" in color.replace(" ", "")):
        return "transparent_text"

    # Fixed typo and added rgb/rgba variations
    light_colors = {"white", "#fff", "#ffffff", "#fffff", "#fefefe", "#fffffe", 
                    "rgb(255,255,255)", "rgba(255,255,255,0)", "rgba(0,0,0,0)", "rgba(0, 0, 0, 0)"}
    if color in light_colors and bg_color in light_colors:
        return "white_on_white"

    if style_dict.get("mso-hide") == "all": return "mso_hide"
    
    # Added height:0px/%, transform:scale(0)
    if re.search(r"height\s*:\s*0(px|%)?", style_dict.get("height", "")): return "clipped_box"
    if "scale(0)" in style_dict.get("transform", ""): return "clipped_box"
    if "clip:rect(0,0,0,0)" in style_dict.get("clip", "") or "rect(0,0,0,0)" in style_dict.get("clip", ""): 
        return "clipped_box"

    for prop in ["left", "top", "right", "bottom", "margin-left"]:
        val = style_dict.get(prop, "")
        m = re.fullmatch(r"(-?[\d.]+)(px|pt|em|rem)?", val)
        if m:
            try:
                num = float(m.group(1))
                unit = m.group(2) or "px"
                if unit == "px" and num <= -500: return "offscreen"
                if unit in ("em", "rem") and num <= -50: return "offscreen"
            except ValueError:
                pass

    # Added text-indent check
    if re.search(r"text-indent\s*:\s*-?\d{4,}px", style_dict.get("text-indent", "")):
        return "offscreen"

    try:
        if float(style_dict.get("opacity", "1")) <= 0.05: return "opacity_zero"
    except ValueError:
        pass

    # Added font-size:0% check
    font_size = style_dict.get("font-size", "")
    if re.search(r"font-size\s*:\s*0(px|%)?", font_size): return "tiny_font"
    m = re.fullmatch(r"([\d.]+)(px|pt|em|rem)?", font_size)
    if m:
        try:
            val = float(m.group(1))
            unit = m.group(2) or "px"
            if unit in ("px", "pt") and val < 2: return "tiny_font"
            elif unit in ("em", "rem") and val < 0.1: return "tiny_font"
        except ValueError:
            return ""
    return ""

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    cyrillic_map = {'\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', '\u0443': 'y', '\u0445': 'x', '\u0456': 'i', '\u0455': 's'}
    text = ''.join(cyrillic_map.get(c, c) for c in text)
    text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u200c", "").replace("\u200d", "")
    return re.sub(r"\s+", " ", text).strip()

def classify_hidden(text: str) -> str:
    if len(text) > 2000:
        text = text[:2000]
    norm_text = normalize_text(text)

    if ("ignore" in norm_text or "disregard" in norm_text or "forget" in norm_text) and \
       ("previous" in norm_text or "above" in norm_text or "prior" in norm_text) and \
       ("instruction" in norm_text or "rule" in norm_text):
        return "hidden_instruction"
    if "system" in norm_text and "override" in norm_text:
        return "hidden_instruction"
    if ("reply" in norm_text or "send" in norm_text) and ("password" in norm_text or "credential" in norm_text):
        return "hidden_instruction"
    if "forward" in norm_text and ("email" in norm_text or "mail" in norm_text) and "@" in norm_text:
        return "hidden_instruction"

    if len(norm_text) <= 200:
        return "hidden_preheader"
    return "hidden_block_large"