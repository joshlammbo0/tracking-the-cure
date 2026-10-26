"""Presentation guards for the redesign: colour tokens, heading order, disclaimer, navigation."""
import html.parser
import re

from pipeline import render
from tools import palette

DISCLAIMER = "Not medical advice. Not investment advice."


def test_colour_tokens_pass_contrast_and_cvd_checks():
    rows, fails = palette.check()
    assert rows and not fails, fails


class Headings(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main, self.levels = False, []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True
        elif self.in_main and re.fullmatch(r"h[1-6]", tag):
            self.levels.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False


def test_rendered_pages(tmp_path):
    out = tmp_path / "site"
    pages = render.render(out)
    for p in pages:
        html = (out / p / "index.html").read_text()
        h = Headings()
        h.feed(html)
        assert h.levels and h.levels[0] == 1, p
        skips = [(a, b) for a, b in zip(h.levels, h.levels[1:]) if b - a > 1]
        assert not skips, (p, skips)
        assert DISCLAIMER in html, p
        for href, _ in render.NAV_PRIMARY + render.NAV_MORE:
            assert href + '"' in html, (p, href)  # every destination reachable from every page
    assert not (out / "styleguide").exists()


def test_hero_chart_plots_model_outputs_unchanged():
    """The homepage context chart must plot model.run() outputs as-is: baseline and displaced, same year."""
    import html as h
    import json
    import yaml
    from pipeline import charts, model
    m = yaml.safe_load(open("data/market.yaml"))
    rows = model.run(m, model.default_inputs(m, "base"))["rows"]
    svg = charts.context_area([r["year"] for r in rows], [r["t1d_baseline_total"] for r in rows],
                              [r["displaced_total"] for r in rows], "t")
    cfg = json.loads(h.unescape(re.search(r'data-chart="([^"]+)"', svg).group(1)))
    base, disp = cfg["series"][0]["values"], cfg["series"][1]["values"]
    assert base == [round(r["t1d_baseline_total"]) for r in rows]
    assert disp == [round(r["displaced_total"]) for r in rows]
    assert all(d <= b for d, b in zip(disp, base))  # displaced is always inside the baseline it is a share of
    assert charts.money(rows[-1]["displaced_total"]) in svg and charts.money(rows[-1]["t1d_baseline_total"]) in svg
