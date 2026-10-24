"""Headline links via Google News RSS. Stores headline, outlet, date, link only — no article text."""
import email.utils
import xml.etree.ElementTree as ET

from .http import get


def headlines(query, n=4):
    r = get("https://news.google.com/rss/search", min_interval=1.0, key="gnews",
            params={"q": query + " when:60d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    root = ET.fromstring(r.content)
    out = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        src = item.find("source")
        outlet = src.text if src is not None else None
        if outlet and title.endswith(" - " + outlet):
            title = title[: -len(outlet) - 3]
        try:
            date = email.utils.parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
        except Exception:
            date = None
        out.append({"title": title, "outlet": outlet, "date": date, "url": item.findtext("link")})
        if len(out) >= n:
            break
    return out
