"""Pipeline section counters must match the program cards listed under them."""
import re

from pipeline import render


def test_section_counters_match_cards(tmp_path):
    out = tmp_path / "site"
    render.render(out)
    html = (out / "pipeline" / "index.html").read_text()
    sections = re.findall(r'<section class="section" id="(\w+)".*?</section>', html, re.S)
    bodies = re.findall(r'<section class="section" id="\w+".*?</section>', html, re.S)
    assert len(bodies) == 4
    total = 0
    for key, sec in zip(sections, bodies):
        m = re.search(r'data-tracked="(\d+)" data-active="(\d+)"', sec)
        cards = re.findall(r'<a class="card"', sec)
        active_cards = re.findall(r'badge good dot">Active', sec)
        assert m and int(m.group(1)) == len(cards) and int(m.group(2)) == len(active_cards), key
        total += len(cards)
    page_total = int(re.search(r"<b>(\d+)</b> cure programs", html).group(1))
    assert total == page_total  # section counts add up to the page total
