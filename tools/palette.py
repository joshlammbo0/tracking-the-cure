"""Validate the colour tokens in site/assets/style.css (development + tests; no Node needed).

Checks, for both the light block (:root) and the dark block (:root[data-theme="dark"]):
  * text pairs meet WCAG AA (4.5:1 body, 3:1 large/graphical)
  * data series reach 3:1 against the chart surface (graphical objects, WCAG 1.4.11)
  * series are distinguishable: OKLab ΔE×100 >= 15 for normal vision and >= 8 under protan/deutan/tritan
    simulation (Machado et al. 2009, severity 1.0) for every pair (only three series, so all pairs)

    python -m tools.palette           # prints a table, exits 1 on any failure
"""
import pathlib
import re
import sys

CSS = pathlib.Path(__file__).resolve().parent.parent / "site" / "assets" / "style.css"

TEXT_PAIRS = [  # (foreground, background, minimum)
    ("ink", "bg", 4.5), ("ink", "surface", 4.5), ("ink", "surface-2", 4.5),
    ("ink-2", "bg", 4.5), ("ink-2", "surface", 4.5), ("ink-2", "surface-2", 4.5),
    ("muted", "bg", 4.5), ("muted", "surface", 4.5), ("muted", "surface-2", 4.5),
    ("accent", "bg", 4.5), ("accent", "surface", 4.5), ("accent", "surface-2", 4.5), ("accent", "accent-soft", 4.5),
    ("good", "bg", 4.5), ("bad", "bg", 4.5), ("good", "surface", 4.5), ("bad", "surface", 4.5),
    ("warn-ink", "warn-bg", 4.5), ("bad", "alert-bg", 4.5), ("accent", "info-bg", 4.5), ("warn-ink", "mine-bg", 4.5),
    ("accent-ink", "accent", 4.5), ("bg", "ink", 4.5),
    ("heat-ink-0", "h0", 4.5), ("heat-ink-1", "h1", 4.5), ("heat-ink-2", "h2", 4.5),
    ("heat-ink-3", "h3", 4.5), ("heat-ink-4", "h4", 4.5), ("heat-ink-5", "h5", 4.5),
]
SERIES = ["s1", "s2", "s3"]

M = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def tokens(css):
    """Return {'light': {...}, 'dark': {...}} from the :root and :root[data-theme="dark"] blocks."""
    def block(sel):
        m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css)
        return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", m.group(1))) if m else {}
    m = re.search(r"/\* 1\. Tokens.*?:root\s*\{(.*?)\n\}", css, re.S)
    light = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)))
    dark = dict(light)
    dark.update(block(':root[data-theme="dark"]'))
    return {"light": light, "dark": dark}


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


def lum(h):
    r, g, b = lin(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def oklab(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def sim(rgb, kind):
    if kind == "normal":
        return rgb
    out = [sum(M[kind][i][j] * rgb[j] for j in range(3)) for i in range(3)]
    return [min(1, max(0, v)) for v in out]


def de(a, b, kind="normal"):
    A, B = oklab(sim(lin(a), kind)), oklab(sim(lin(b), kind))
    return 100 * sum((x - y) ** 2 for x, y in zip(A, B)) ** 0.5


def check(css=None):
    css = css or CSS.read_text()
    rows, fails = [], []
    for mode, t in tokens(css).items():
        for fg, bg, need in TEXT_PAIRS:
            if fg not in t or bg not in t:
                continue
            r = contrast(t[fg], t[bg])
            rows.append((mode, "text", fg + " on " + bg, round(r, 2), need))
            if r < need:
                fails.append((mode, fg, bg, round(r, 2)))
        for s in SERIES:
            r = contrast(t[s], t["surface"])
            rows.append((mode, "graphic", s + " on surface", round(r, 2), 3))
            if r < 3:
                fails.append((mode, s, "surface", round(r, 2)))
        for i, a in enumerate(SERIES):
            for b in SERIES[i + 1:]:
                for kind, need in (("normal", 15), ("protan", 8), ("deutan", 8), ("tritan", 8)):
                    d = de(t[a], t[b], kind)
                    rows.append((mode, "ΔE " + kind, a + " vs " + b, round(d, 1), need))
                    if d < need:
                        fails.append((mode, a + "/" + b, kind, round(d, 1)))
    return rows, fails


if __name__ == "__main__":
    rows, fails = check()
    for r in rows:
        print("{:5} {:10} {:26} {:>7}  (min {})".format(*r))
    print("\nFAILURES:" if fails else "\nAll colour checks pass.", *fails, sep="\n  ")
    sys.exit(1 if fails else 0)
