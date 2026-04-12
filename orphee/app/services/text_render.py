import os
import re

from PIL import Image, ImageDraw, ImageFont

EMOJI_FONT_PATH = "/app/fonts/Apple-Color-Emoji.ttc"

# Apple Color Emoji est une police bitmap — tailles disponibles uniquement
_EMOJI_SIZES = [20, 32, 40, 48, 64, 96, 160]

def _nearest_emoji_size(size: int) -> int:
    return min(_EMOJI_SIZES, key=lambda s: abs(s - size))

# Matches common emoji Unicode ranges (including ZWJ sequences)
_EMOJI_RE = re.compile(
    r"["
    r"\U0001F000-\U0001FFFF"
    r"\U00002600-\U000027BF"
    r"\U0001F900-\U0001FAFF"
    r"\uFE00-\uFE0F"
    r"\u200D"
    r"\u20E3"
    r"\u2300-\u23FF"
    r"\u2B00-\u2BFF"
    r"]+",
    re.UNICODE,
)


def _parse_color(color: str) -> tuple[int, int, int, int]:
    """Converts '0xRRGGBB' or 'white'/'black' fallbacks to RGBA tuple."""
    raw = (color or "0xFFFFFF").strip()
    if raw.lower() == "white":
        return (255, 255, 255, 255)
    if raw.lower() == "black":
        return (0, 0, 0, 255)
    if raw.lower().startswith("0x") and len(raw) == 8:
        r = int(raw[2:4], 16)
        g = int(raw[4:6], 16)
        b = int(raw[6:8], 16)
        return (r, g, b, 255)
    return (255, 255, 255, 255)


def _split_runs(text: str) -> list[tuple[str, bool]]:
    """Splits text into (substring, is_emoji) runs."""
    runs: list[tuple[str, bool]] = []
    pos = 0
    for m in _EMOJI_RE.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], False))
        runs.append((m.group(), True))
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], False))
    return runs or [("", False)]


_EMOJI_AVAIL: bool = os.path.exists(EMOJI_FONT_PATH)
_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}

def _load_font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    key = (path, size, index)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size, index=index)
    return _FONT_CACHE[key]


def render_text_png(
    text: str,
    font_path: str,
    size: int,
    color: str,
    border_w: int,
    output_path: str,
) -> tuple[int, int]:
    """Renders a mixed text+emoji string onto a transparent PNG.

    Returns (image_width, image_height).
    """
    fill        = _parse_color(color)
    stroke_fill = (0, 0, 0, 255)

    runs = _split_runs(text)

    text_font  = _load_font(font_path, size)
    emoji_size = _nearest_emoji_size(size)
    emoji_font = _load_font(EMOJI_FONT_PATH, emoji_size, index=0) if _EMOJI_AVAIL else text_font

    # ── Measure each run ────────────────────────────────────────────────────────
    tmp_img  = Image.new("RGBA", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)

    metrics: list[tuple[int, int, int]] = []  # (width, height, top_offset)
    for run_text, is_emoji_run in runs:
        font = emoji_font if is_emoji_run else text_font
        sw   = 0 if is_emoji_run else border_w
        bbox = tmp_draw.textbbox((0, 0), run_text, font=font, stroke_width=sw)
        w    = max(bbox[2] - bbox[0], 1)
        h    = max(bbox[3] - bbox[1], 1)
        metrics.append((w, h, bbox[1]))

    total_w = sum(m[0] for m in metrics)
    total_h = max(m[1] for m in metrics) if metrics else size

    canvas_w = total_w + 2
    canvas_h = total_h + 2

    # ── Render ──────────────────────────────────────────────────────────────────
    img  = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = 0
    for (run_text, is_emoji_run), (rw, _rh, rtop) in zip(runs, metrics):
        font = emoji_font if is_emoji_run else text_font
        y    = -rtop  # align tops of all runs

        if is_emoji_run:
            draw.text((x, y), run_text, font=font, embedded_color=True)
        else:
            draw.text(
                (x, y), run_text, font=font,
                fill=fill,
                stroke_width=border_w,
                stroke_fill=stroke_fill,
            )
        x += rw

    img.save(output_path, "PNG")
    return (canvas_w, canvas_h)
