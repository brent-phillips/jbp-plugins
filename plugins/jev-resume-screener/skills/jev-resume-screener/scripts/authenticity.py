"""Authenticity checks that code can do exactly: the resume's own timeline.

Everything here runs locally on the redacted text. Each check returns plain
findings for a human to verify; none of them changes the fit index, and none
of them is a reason to reject. Employment gaps are deliberately not checked
(see references/rubric-guide.md).
"""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
ROLE_LINE = re.compile(
    rf"^(?P<head>.+?)\s*[|,]\s*(?P<m1>{_MON}\s+)?(?P<y1>(?:19|20)\d\d)\s*[-–—to]+\s*"
    rf"(?:(?P<m2>{_MON}\s+)?(?P<y2>(?:19|20)\d\d)|(?P<now>present|current|now))\s*$",
    re.I,
)
DEGREE_LINE = re.compile(
    r"^\W*(?:b\.?\s?[sa]\.?|bachelor|m\.?\s?[sa]\.?|master|b\.?\s?eng|m\.?\s?eng|mba|ph\.?d)\b.*?"
    r"((?:19|20)\d\d)\s*$",
    re.I,
)
PART_TIME = re.compile(r"\b(contract|contractor|freelance|consultant|advisor|adviser|part[- ]time|"
                       r"volunteer|board|adjunct|instructor|fractional)\b", re.I)

# Seniority ladder for title-jump detection. First match wins, so a junior or
# associate qualifier outranks the "engineer" it modifies.
LEVELS = [
    (1, r"\b(junior|jr\.?|associate|intern|trainee|apprentice)\b"),
    (8, r"\b(cto|chief)\b"),
    (7, r"\b(vp|vice president|head of)\b"),
    (6, r"\b(director|senior manager|sr\.? manager)\b"),
    (5, r"\b(manager|leader)\b"),
    (4, r"\b(lead|staff|principal|architect)\b"),
    (3, r"\b(senior|sr\.?)\b"),
    (2, r"\b(engineer|administrator|developer|analyst|specialist)\b"),
]

# Year a tool became generally available. "N years of X" beyond this is impossible.
TOOL_SINCE = {
    "kubernetes": 2014, "k8s": 2014, "terraform": 2014, "docker": 2013, "eks": 2018,
    "github actions": 2019, "argo cd": 2018, "argocd": 2018, "istio": 2017, "linkerd": 2016,
    "helm": 2016, "pulumi": 2018, "gitops": 2017, "prometheus": 2015, "openshift": 2011,
    "aws lambda": 2014, "lambda": 2014, "flux": 2016, "backstage": 2020,
}
YEARS_OF = re.compile(
    r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:hands-on\s+|production\s+|deep\s+)?"
    r"(?:experience\s+(?:with|in|running|using)\s+)?([a-z0-9][a-z0-9 .]{1,24})", re.I)

# Stock phrases that LLM-written or template resumes lean on. A weak signal on its own.
GENERIC_PHRASES = [
    "results-driven", "results driven", "dynamic", "synergy", "synergies", "leverage",
    "leveraged", "leveraging", "spearheaded", "visionary", "thought leader", "best-in-class",
    "world-class", "cutting-edge", "cutting edge", "passionate", "proven track record",
    "detail-oriented", "self-starter", "go-getter", "game-changer", "paradigm", "holistic",
    "robust", "seamless", "seamlessly", "transformative", "innovative", "strategic thinker",
    "drive innovation", "drove innovation", "fast-paced", "value-add", "move the needle",
    "deep dive", "end-to-end", "north star", "best practices", "cross-functional synergy",
]


def _month(m: str | None, default: int) -> int:
    return MONTHS.get(m.strip(". ").lower()[:3], default) if m else default


def parse_roles(text: str, today: date | None = None) -> list[dict]:
    today = today or date.today()
    roles = []
    for line in text.splitlines():
        line = line.strip().lstrip("•*-· ").strip()
        m = ROLE_LINE.match(line)
        if not m:
            continue
        start = int(m["y1"]) * 12 + _month(m["m1"], 1) - 1
        if m["now"]:
            end = today.year * 12 + today.month - 1
        else:
            end = int(m["y2"]) * 12 + _month(m["m2"], 12) - 1
        if end < start:
            continue
        head = m["head"]
        title = re.split(r"\s*[|,@]\s*|\s+at\s+", head)[0]
        roles.append({"line": line, "title": title, "start": start, "end": end,
                      "months": end - start, "part_time": bool(PART_TIME.search(head))})
    return roles


def _level(title: str) -> int | None:
    t = title.lower()
    for lvl, pat in LEVELS:
        if re.search(pat, t):
            return lvl
    return None


def _ym(n: int) -> str:
    return f"{n // 12}-{n % 12 + 1:02d}"


def check(text: str, cfg: dict, today: date | None = None) -> dict:
    today = today or date.today()
    roles = parse_roles(text, today)
    findings = []

    # 1. overlapping full-time roles
    ft = [r for r in roles if not r["part_time"]]
    for i in range(len(ft)):
        for j in range(i + 1, len(ft)):
            a, b = ft[i], ft[j]
            overlap = min(a["end"], b["end"]) - max(a["start"], b["start"])
            if overlap >= cfg["auth_overlap_months"]:
                findings.append({
                    "check": "overlapping roles",
                    "detail": f"'{a['title']}' and '{b['title']}' overlap by {overlap} months "
                              f"({_ym(max(a['start'], b['start']))} to {_ym(min(a['end'], b['end']))})"})

    # 2. degree dated well after the first professional role
    first = min((r["start"] for r in ft), default=None)
    degrees = [int(m.group(1)) for line in text.splitlines()
               if (m := DEGREE_LINE.match(line.strip()))]
    if first is not None and degrees:
        first_degree = min(degrees)
        lag = first_degree - first // 12
        if lag >= cfg["auth_degree_lag_years"]:
            findings.append({
                "check": "degree after career start",
                "detail": f"earliest degree dated {first_degree}, {lag} years after the first "
                          f"listed role began ({first // 12})"})

    # 3. title jumps: ordered by start date, compare each role with the one before it
    ordered = sorted((r for r in ft if _level(r["title"]) is not None), key=lambda r: r["start"])
    for prev, cur in zip(ordered, ordered[1:]):
        jump = _level(cur["title"]) - _level(prev["title"])
        if jump >= cfg["auth_title_jump_levels"]:
            findings.append({
                "check": "title jump",
                "detail": f"'{prev['title']}' to '{cur['title']}' with no step in between"})

    # 4. very short tenure in a senior role
    for r in ft:
        lvl = _level(r["title"]) or 0
        ongoing = r["end"] >= today.year * 12 + today.month - 2
        if lvl >= 5 and r["months"] < cfg["auth_short_senior_months"] and not ongoing:
            findings.append({
                "check": "short senior tenure",
                "detail": f"'{r['title']}' lasted {r['months']} months"})

    # 5. more years with a tool than the tool has existed
    for m in YEARS_OF.finditer(text):
        n, rest = int(m.group(1)), m.group(2).lower()
        for tool, since in TOOL_SINCE.items():
            if re.match(rf"{re.escape(tool)}\b", rest) or re.search(rf"\b{re.escape(tool)}\b", rest[:20]):
                if n > today.year - since + cfg["auth_tool_slack_years"]:
                    findings.append({
                        "check": "tool older than it exists",
                        "detail": f"claims {n} years of {tool}, which dates from {since}"})
                break

    # 6. certification count far beyond what the experience suggests
    certs = _section_items(text, r"certifications?|licen[cs]es|credentials")
    if len(certs) >= cfg["auth_cert_count"]:
        findings.append({"check": "certification count",
                         "detail": f"{len(certs)} certifications listed"})

    # 7. stock phrasing density (weak signal, reported but flagged only when heavy)
    words = max(1, len(re.findall(r"\w+", text)))
    low = text.lower()
    hits = sorted({p for p in GENERIC_PHRASES if p in low})
    per_k = round(1000 * sum(low.count(p) for p in hits) / words, 1)

    return {"roles_parsed": len(roles), "findings": findings,
            "generic_phrases": hits, "generic_per_1k_words": per_k}


def _section_items(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    items, inside = [], False
    for line in lines:
        s = line.strip()
        if re.fullmatch(rf"(?i)({heading})\s*:?", s):
            inside = True
            continue
        if inside:
            if not s:
                if items:
                    break
                continue
            if s.isupper() or re.fullmatch(r"[A-Z][A-Za-z &/]+:?", s) and len(s.split()) <= 4:
                break
            items.extend(x for x in re.split(r"\s*[;,]\s*(?![^()]*\))", s.lstrip("•*-· ")) if x)
    return items
