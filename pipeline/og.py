"""Open Graph / Twitter share images (1200x630 PNG), drawn with Pillow.

Images are cached in site/assets/og/ and only drawn when missing, so the committed set
stays stable and CI only draws images for pages added since. They carry no live numbers,
so they never go stale. Delete a file to force a redraw.
"""
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "site" / "assets" / "og"
W, H = 1200, 630
BG, INK, MUTED, ACCENT, RULE = (11, 19, 34), (233, 237, 243), (151, 163, 182), (92, 195, 222), (51, 67, 95)  # navy theme tokens

SERIF = ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]
SANS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
SANS_REG = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def _font(paths, size):
    from PIL import ImageFont
    for p in paths:
        if pathlib.Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def ensure(name, title, kicker, track=None):
    """track=(evidence_index, stage_index) draws that program's real evidence-gap track; None draws none."""
    path = DIR / name
    if path.exists():
        return path
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # Pillow missing: pages still render, just without a fresh image
        return None
    DIR.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    pad = 80
    # brand mark: rising line in a rounded square
    d.rounded_rectangle([pad, pad, pad + 56, pad + 56], radius=12, fill=ACCENT)
    d.line([(pad + 12, pad + 40), (pad + 24, pad + 28), (pad + 32, pad + 34), (pad + 46, pad + 16)], fill=BG, width=6, joint="curve")
    d.text((pad + 76, pad + 4), "Tracking the Cure", font=_font(SERIF, 34), fill=INK)
    d.text((pad + 78, pad + 44), "INDEPENDENT RESEARCH · TYPE 1 DIABETES", font=_font(SANS, 15), fill=MUTED)
    d.text((pad, 238), kicker.upper(), font=_font(SANS, 22), fill=ACCENT)
    size = 64 if len(title) < 34 else 54 if len(title) < 60 else 46
    f = _font(SERIF, size)
    width = 30 if size == 64 else 38 if size == 54 else 44
    y = 280
    for line in textwrap.wrap(title, width=width)[:3]:
        d.text((pad, y), line, font=f, fill=INK)
        y += int(size * 1.18)
    if track is not None:  # the program's own grades (filled dot = results reported, ring = stage reached)
        ev, st = track
        ty, x0, x1 = H - 150, W - pad - 360, W - pad
        d.line([(x0, ty), (x1, ty)], fill=RULE, width=2)
        for k in range(6):
            cx = x0 + (k + 0.5) * (x1 - x0) / 6
            d.line([(cx, ty - 6), (cx, ty + 6)], fill=RULE, width=2)
        ex, sx = x0 + (ev + 0.5) * (x1 - x0) / 6, x0 + (st + 0.5) * (x1 - x0) / 6
        for xx in range(int(ex) + 12, int(sx) - 12, 14):
            d.line([(xx, ty), (xx + 7, ty)], fill=INK, width=3)
        if st > ev:
            d.ellipse([sx - 10, ty - 10, sx + 10, ty + 10], fill=BG, outline=INK, width=3)
        d.ellipse([ex - 10, ty - 10, ex + 10, ty + 10], fill=INK)
    d.line([(pad, H - 110), (W - pad, H - 110)], fill=RULE, width=2)
    d.text((pad, H - 86), "Stage vs. evidence · Cure Impact Model · Catalysts · Every number sourced",
           font=_font(SANS_REG, 22), fill=MUTED)
    im.save(path, "PNG", optimize=True)
    return path


def favicon(path):
    """favicon.ico for browsers that ignore the SVG icon (same mark as the masthead)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 63, 63], radius=14, fill=(11, 106, 134))
    d.line([(14, 44), (26, 32), (34, 38), (50, 18)], fill=(255, 255, 255), width=6, joint="curve")
    im.save(path, sizes=[(16, 16), (32, 32), (48, 48)])
    return path
