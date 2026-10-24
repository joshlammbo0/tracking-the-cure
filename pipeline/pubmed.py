"""PubMed E-utilities: recent citations only (title, journal, date, link). No abstracts copied."""
import os

from .http import get

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
API_KEY = os.environ.get("NCBI_API_KEY")  # optional; raises the rate limit
INTERVAL = 0.12 if API_KEY else 0.4


def _params(extra):
    p = {"db": "pubmed", "retmode": "json", "tool": "tracking-the-cure"}
    if API_KEY:
        p["api_key"] = API_KEY
    p.update(extra)
    return p


def recent(term, days=365, retmax=8):
    ids = get(BASE + "esearch.fcgi", min_interval=INTERVAL, key="pubmed", params=_params({
        "term": term, "sort": "pub_date", "retmax": retmax, "datetype": "pdat", "reldate": days,
    })).json()["esearchresult"]["idlist"]
    if not ids:
        return []
    res = get(BASE + "esummary.fcgi", min_interval=INTERVAL, key="pubmed",
              params=_params({"id": ",".join(ids)})).json()["result"]
    out = []
    for pmid in ids:
        r = res.get(pmid)
        if not r:
            continue
        doi = next((a["value"] for a in r.get("articleids", []) if a["idtype"] == "doi"), None)
        types = r.get("pubtype", [])
        out.append({
            "pmid": pmid,
            "title": r.get("title", "").rstrip("."),
            "journal": r.get("source"),
            "pubdate": r.get("pubdate"),
            "sortdate": r.get("sortpubdate", "")[:10].replace("/", "-"),
            "authors": ", ".join(a["name"] for a in r.get("authors", [])[:3]) + (" et al." if len(r.get("authors", [])) > 3 else ""),
            "is_rct": any("Randomized Controlled Trial" in t for t in types),
            "is_review": any(t in ("Review", "Systematic Review", "Meta-Analysis") for t in types),
            "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
            "doi": doi,
        })
    return out
