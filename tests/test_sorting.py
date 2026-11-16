"""Regression test for the shared table sorter in site/assets/app.js.

Bug fixed: sort keys went through parseFloat, so ISO dates in the same year ("2026-09-17", "2026-11-30") all
became 2026 and tied. Runs the real app.js in headless Chromium; skipped where Playwright isn't installed
(the CI validate job installs only pytest).
"""
import pathlib

import pytest

playwright = pytest.importorskip("playwright.sync_api")

APP_JS = pathlib.Path(__file__).resolve().parent.parent / "site" / "assets" / "app.js"

PAGE = """<!doctype html><html><body>
<table class="data sortable" id="t">
  <thead><tr><th>Event</th><th>Date</th><th>Enrolment</th></tr></thead>
  <tbody>
    <tr><td>c</td><td data-sort="2026-11-30">Nov 30</td><td data-sort="905">905</td></tr>
    <tr><td>a</td><td data-sort="2026-09-17">Sep 17</td><td data-sort="60">60</td></tr>
    <tr><td>m</td><td data-sort="">—</td><td data-sort="">—</td></tr>
    <tr><td>d</td><td data-sort="2026-11">Nov 2026</td><td data-sort="1398">1398</td></tr>
    <tr><td>b</td><td data-sort="2026-10-27">Oct 27</td><td data-sort="18">18</td></tr>
    <tr><td>e</td><td data-sort="2027-01-28">Jan 28</td><td data-sort="465">465</td></tr>
  </tbody>
</table>
<script>window.TTC = {};</script>
<script>%s</script>
</body></html>"""


def order(page):
    return page.eval_on_selector_all("#t tbody tr", "rs => rs.map(r => r.cells[0].textContent)")


@pytest.fixture(scope="module")
def page():
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # browsers not installed
            pytest.skip("Chromium not available: {}".format(e))
        pg = browser.new_page()
        pg.set_content(PAGE % APP_JS.read_text())
        yield pg
        browser.close()


def test_dates_sort_by_full_iso_date_missing_last(page):
    page.click("#t thead th:nth-child(2) button")  # ascending
    # "2026-11" has month precision and sorts as the end of November, so after Nov 30
    assert order(page) == ["a", "b", "c", "d", "e", "m"]
    page.click("#t thead th:nth-child(2) button")  # descending
    assert order(page) == ["e", "d", "c", "b", "a", "m"]  # missing date still last


def test_numbers_still_sort_numerically(page):
    page.click("#t thead th:nth-child(3) button")
    assert order(page) == ["b", "a", "e", "c", "d", "m"]  # 18, 60, 465, 905, 1398, missing
    page.click("#t thead th:nth-child(3) button")
    assert order(page) == ["d", "c", "e", "a", "b", "m"]
