"""ClinicalTrials.gov API v2."""
from .http import get

BASE = "https://clinicaltrials.gov/api/v2/studies"

PHASE_LABEL = {
    "EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1", "PHASE2": "Phase 2",
    "PHASE3": "Phase 3", "PHASE4": "Phase 4", "NA": "N/A",
}
# Highest registry phase → evidence-grade vocabulary used on the site.
PHASE_GRADE = {"EARLY_PHASE1": "phase1", "PHASE1": "phase1", "PHASE2": "phase2",
               "PHASE3": "phase3", "PHASE4": "approved"}
GRADE_ORDER = ["preclinical", "phase1", "phase2", "phase3", "filed", "approved"]


def _date(struct):
    if not struct:
        return None, None
    return struct.get("date"), struct.get("type")


def parse(study):
    p = study["protocolSection"]
    ident, status = p["identificationModule"], p["statusModule"]
    design = p.get("designModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name")
    phases = design.get("phases") or []
    pcd, pcd_type = _date(status.get("primaryCompletionDateStruct"))
    cd, cd_type = _date(status.get("completionDateStruct"))
    enroll = design.get("enrollmentInfo") or {}
    # Combined phases (e.g. Phase 1/2) grade at the LOWER phase — the conservative read.
    grades = [PHASE_GRADE[x] for x in phases if x in PHASE_GRADE]
    if len(grades) > 1:
        grades = [min(grades, key=GRADE_ORDER.index)]
    return {
        "nct_id": ident["nctId"],
        "title": ident.get("briefTitle"),
        "acronym": ident.get("acronym"),
        "status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "phases": [PHASE_LABEL.get(x, x) for x in phases],
        "phase_grade": max(grades, key=GRADE_ORDER.index) if grades else None,
        "sponsor": sponsor,
        "sponsor_class": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class"),
        "conditions": p.get("conditionsModule", {}).get("conditions", []),
        "enrollment": enroll.get("count"),
        "enrollment_type": enroll.get("type"),
        "start_date": (status.get("startDateStruct") or {}).get("date"),
        "primary_completion": pcd,
        "primary_completion_type": pcd_type,
        "completion": cd,
        "completion_type": cd_type,
        "last_update": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
        "has_results": study.get("hasResults", False),
        "url": "https://clinicaltrials.gov/study/" + ident["nctId"],
    }


def fetch_study(nct_id):
    return parse(get(BASE + "/" + nct_id, params={"format": "json"}, min_interval=0.25).json())


def search(term, condition="type 1 diabetes", statuses=None, page_size=50):
    params = {"query.cond": condition, "query.term": term, "pageSize": page_size,
              "sort": "LastUpdatePostDate:desc", "format": "json"}
    if statuses:
        params["filter.overallStatus"] = ",".join(statuses)
    data = get(BASE, params=params, min_interval=0.25).json()
    return [parse(s) for s in data.get("studies", [])]
