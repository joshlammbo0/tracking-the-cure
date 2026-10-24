"""Render the whole site from the committed data into a temp dir and sanity-check it."""
import re

from pipeline import render


def test_render_site(tmp_path):
    out = tmp_path / "site"
    pages = render.render(out)
    assert "" in pages and "model/" in pages and "catalysts/" in pages
    assert (out / "catalysts.ics").read_text().startswith("BEGIN:VCALENDAR")
    assert (out / "model" / "cure-impact-model.csv").exists()
    assert (out / "sitemap.xml").exists() and (out / "404.html").exists()
    for p in pages:
        html = (out / p / "index.html").read_text()
        assert "<title>" in html and 'name="description"' in html and 'og:image' in html, p
        assert "Not investment advice" in html, p
        # Python reprs must never leak into the page.
        assert not re.search(r"(?<!class=\"v\")>\s*(None|nan|Undefined)\s*<", html), p


def test_internal_links_resolve(tmp_path):
    out = tmp_path / "site"
    render.render(out)
    missing = set()
    for f in out.rglob("*.html"):
        if f.name == "404.html":
            continue
        for href in re.findall(r'href="([^"#?]+)', f.read_text()):
            if href.startswith(("http", "mailto:", "data:", "webcal:")):
                continue
            target = (f.parent / href).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                missing.add("{} -> {}".format(f.relative_to(out), href))
    assert not missing, sorted(missing)[:20]
