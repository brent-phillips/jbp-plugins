#!/usr/bin/env python3
"""Learning loop: turn a reviewer's verdicts into lessons that later runs apply.

  run.sh feedback.py compare --out <run> --decisions decisions.csv
      Lists where the reviewer and the screener disagree, with the evidence behind
      each screener call, so Claude can ask the reviewer why.
  run.sh feedback.py log --out <run> --entry entry.json
      Appends a reviewed lesson to the learning log.
  run.sh feedback.py show --role "<role>"
      Prints the lessons for this role (and general ones) for the next rubric draft.

decisions.csv has columns file,decision[,note]; decision is advance, maybe, or reject
(yes/no also work). The log lives in ~/.jev-screener/learnings/ (override with
JEV_SCREENER_HOME), outside any repository: it can describe real candidates.
Lessons refer to candidates by ID only.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HOME = Path(os.environ.get("JEV_SCREENER_HOME", Path.home() / ".jev-screener"))
LOG_DIR = HOME / "learnings"
VERDICT = {"advance": 2, "yes": 2, "maybe": 1, "reject": 0, "no": 0}
TIER = {"Strong": 2, "Possible": 1, "Unlikely": 0}


def slug(role: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "general"


def log_path(role: str) -> Path:
    return LOG_DIR / f"{slug(role)}.jsonl"


def compare(out: Path, decisions: Path) -> None:
    res = json.loads((out / "results.json").read_text())
    by_file = {c["file"]: c for c in res["candidates"]}
    rows = list(csv.DictReader(decisions.open(encoding="utf-8")))
    agree, gaps, unknown, gate_hits = 0, [], [], []
    for r in rows:
        c = by_file.get(r["file"].strip())
        v = VERDICT.get(r.get("decision", "").strip().lower())
        if c is None or v is None or c.get("tier") not in TIER:
            unknown.append(r.get("file"))
            continue
        t = TIER[c["tier"]]
        if t == v:
            agree += 1
            continue
        low_gates = [k for k, p in c.get("must_haves", {}).items() if p < 0.35]
        if v > t and low_gates:
            gate_hits.extend(low_gates)
        gaps.append({
            "id": c["id"], "reviewer": r["decision"].strip().lower(), "screener": c["tier"],
            "direction": "screener too low" if v > t else "screener too high",
            "reviewer_note": (r.get("note") or "").strip(),
            "fit_index": c.get("fit_index"),
            "must_haves": c.get("must_haves", {}),
            "scored": {k: s["norm"] for k, s in c.get("scored", {}).items()},
            "flags": c.get("flags", []),
        })
    n = agree + len(gaps)
    gate_advice = [
        f"must-have '{g}' sank {k} candidate(s) the reviewer rated higher; consider making it a "
        f"scored criterion (see rubric_check.py)"
        for g, k in sorted(((g, gate_hits.count(g)) for g in set(gate_hits)), key=lambda x: -x[1])]
    print(json.dumps({"role": res.get("role", ""), "compared": n,
                      "agreement": f"{agree}/{n}" if n else "0/0",
                      "gate_advice": gate_advice,
                      "disagreements": gaps, "not_matched": unknown}, indent=2))


def log(out: Path, entry_file: Path) -> None:
    entry = json.loads(entry_file.read_text())
    res = json.loads((out / "results.json").read_text())
    role = entry.get("role") or res.get("role") or "general"
    entry = {"date": date.today().isoformat(), "role": role, "run": str(out.resolve()), **entry}
    if not entry.get("lesson"):
        sys.exit("entry needs a 'lesson'")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(LOG_DIR, 0o700)
    path = log_path(role if entry.get("scope", "role") == "role" else "general")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"logged to {path}")


def show(role: str) -> None:
    seen = False
    sources = [(log_path(role), f"role: {role}")]
    if slug(role) != "general":
        sources.append((log_path("general"), "all roles"))
    for path, label in sources:
        if not path.exists():
            continue
        lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        if not lines:
            continue
        seen = True
        print(f"## Lessons ({label}), oldest first")
        for e in lines:
            change = f" -> {e['rubric_change']}" if e.get("rubric_change") else ""
            print(f"- {e['date']}: {e['lesson']}{change}")
    if not seen:
        print("No lessons logged yet for this role.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--decisions", required=True, type=Path)
    lg = sub.add_parser("log")
    lg.add_argument("--out", required=True, type=Path)
    lg.add_argument("--entry", required=True, type=Path)
    s = sub.add_parser("show")
    s.add_argument("--role", required=True)
    a = ap.parse_args()
    if a.cmd == "compare":
        compare(a.out, a.decisions)
    elif a.cmd == "log":
        log(a.out, a.entry)
    else:
        show(a.role)


if __name__ == "__main__":
    main()
