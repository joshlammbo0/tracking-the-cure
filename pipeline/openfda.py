"""openFDA: device decisions in diabetes-relevant product codes, plus GLP-1 label checks."""
import datetime as dt
import re

from .http import get

DEVICE_CODES = {
    "QBJ": "Integrated CGM (iCGM)",
    "SAF": "OTC CGM",
    "SBH": "OTC CGM",
    "SJD": "Integrated glucose-ketone monitor",
    "QFG": "Alternate controller enabled (ACE) insulin pump",
    "QJI": "Interoperable automated glycemic controller (AID algorithm)",
    "QRX": "Insulin dosing software",
    "MDS": "CGM (PMA)",
    "QHJ": "Implantable CGM (PMA)",
    "QCD": "Implantable CGM (PMA)",
    "OZP": "Closed-loop insulin system (PMA)",
    "SFI": "CGM sensor (PMA)",
}


def device_decisions(days=730, limit=100):
    since = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")
    today = dt.date.today().strftime("%Y%m%d")
    codes = " OR ".join(DEVICE_CODES)
    rng = "[{} TO {}]".format(since, today)
    out = []
    r = get("https://api.fda.gov/device/510k.json", min_interval=0.3, params={
        "search": "product_code:({}) AND decision_date:{}".format(codes, rng),
        "sort": "decision_date:desc", "limit": limit}).json()
    for x in r.get("results", []):
        num = x["k_number"]
        kind = "De Novo" if num.startswith("DEN") else "510(k)"
        page = "denovo.cfm" if kind == "De Novo" else "pmn.cfm"
        out.append({
            "number": num, "kind": kind, "date": _iso(x.get("decision_date")),
            "device": x.get("device_name"), "applicant": x.get("applicant"),
            "product_code": x.get("product_code"), "code_label": DEVICE_CODES.get(x.get("product_code")),
            "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/{}?ID={}".format(page, num),
        })
    # PMA originals and panel-track/180-day supplements only (skip manufacturing-site noise).
    r = get("https://api.fda.gov/device/pma.json", min_interval=0.3, params={
        "search": "product_code:(MDS OR QHJ OR QCD OR OZP OR SFI) AND decision_date:{}".format(rng),
        "sort": "decision_date:desc", "limit": limit}).json()
    for x in r.get("results", []):
        reason = (x.get("supplement_reason") or "").lower()
        sup = x.get("supplement_number") or ""
        if sup and not re.search(r"indication|new|design|labeling change - indications", reason):
            continue
        num = x["pma_number"] + ("/" + sup if sup else "")
        out.append({
            "number": num, "kind": "PMA" + (" supplement" if sup else ""), "date": _iso(x.get("decision_date")),
            "device": x.get("trade_name"), "applicant": x.get("applicant"),
            "product_code": x.get("product_code"), "code_label": DEVICE_CODES.get(x.get("product_code")),
            "note": x.get("supplement_reason"),
            "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id=" + x["pma_number"],
        })
    out.sort(key=lambda d: d["date"] or "", reverse=True)
    return out


def _iso(s):
    if not s:
        return None
    return s if "-" in s else "{}-{}-{}".format(s[:4], s[4:6], s[6:8])


GLP1_LABELS = ["Ozempic", "Wegovy", "Mounjaro", "Zepbound", "Victoza", "Trulicity", "Rybelsus"]


def glp1_label_checks():
    """For each GLP-1 brand, find what the current FDA label says about type 1 diabetes."""
    out = []
    for brand in GLP1_LABELS:
        r = get("https://api.fda.gov/drug/label.json", min_interval=0.3, params={
            "search": 'openfda.brand_name:"{}"'.format(brand), "limit": 1,
            "sort": "effective_time:desc"}).json()
        res = (r.get("results") or [None])[0]
        if not res:
            out.append({"brand": brand, "found": False})
            continue
        text = " ".join(res.get("indications_and_usage", []))
        sentences = re.split(r"(?<=[.])\s+", re.sub(r"\s+", " ", text))
        t1d = [s.strip() for s in sentences if re.search(r"type 1 diabetes", s, re.I)]
        positive = [s for s in t1d if not re.search(r"\bnot\b|has not been studied|should not", s, re.I)]
        mentions_t2d = bool(re.search(r"type 2 diabetes", text, re.I))
        mentions_weight = bool(re.search(r"weight|obesity|BMI", text, re.I))
        scope = " and ".join(x for x, ok in (("type 2 diabetes", mentions_t2d), ("weight management / obesity-related", mentions_weight)) if ok)
        out.append({
            "brand": brand, "found": True,
            "generic": ", ".join(res.get("openfda", {}).get("generic_name", [])),
            "manufacturer": ", ".join(res.get("openfda", {}).get("manufacturer_name", [])),
            "effective": _iso(res.get("effective_time")),
            "t1d_statement": t1d[0][:300] if t1d else None,
            "indication_scope": scope or "see label",
            "approved_for_t1d": bool(positive),
            "url": "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=" + brand,
        })
    return out
