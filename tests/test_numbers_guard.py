"""The redesign's numerical guard must catch silent changes and tolerate pure moves."""
from tools import numbers


def site(items, model=None, csv="x"):
    return {"pages": {"index.html": items}, "model": model or {"a": 1.0}, "csv_sha256": csv}


def item(text, heading="H", region="main"):
    return {"text": text, "heading": heading, "region": region, "el": "p"}


def test_rounding_change_blocks():
    rep = numbers.compare(site([item("$1.4B")]), site([item("$1.38B")]), {})
    assert rep["blocking"]
    assert rep["pages"]["index.html"]["removed"] == ["$1.4B"] and rep["pages"]["index.html"]["added"] == ["$1.38B"]


def test_lost_caveat_blocks():
    rep = numbers.compare(site([item("Model output, not a forecast.")]), site([]), {})
    assert rep["blocking"]


def test_move_is_reported_but_not_blocking():
    rep = numbers.compare(site([item("20.9%", heading="Old")]), site([item("20.9%", heading="New")]), {})
    assert not rep["blocking"] and rep["pages"]["index.html"]["moved"] == ["20.9%"]


def test_model_or_csv_change_blocks():
    assert numbers.compare(site([], {"a": 1.0}), site([], {"a": 1.0000001}), {})["blocking"]
    assert numbers.compare(site([], csv="x"), site([], csv="y"), {})["blocking"]


def test_approved_change_passes():
    approved = {"removed": [{"page": "index.html", "text": "old headline 48B"}],
                "added": [{"page": "index.html", "text": "new headline 48B"}]}
    rep = numbers.compare(site([item("old headline 48B")]), site([item("new headline 48B")]), approved)
    assert not rep["blocking"]
