#!/usr/bin/env python3
"""Recommend, for each rubric criterion, whether it should be a hard gate or a score.

  run.sh rubric_check.py --rubric rubric.json [--out <run>]

A must-have is a hard gate: the fit index multiplies its probability, so a
candidate at p=0.1 is sunk however strong they are elsewhere. That suits facts a
candidate either has or lacks. It does not suit quantities where "close" still
counts, such as years of experience: 2.5 years against a 3-year bar is a near
miss, not a no. Those belong in `scored`, with bands as levels, so proximity
earns partial credit.

Without --out, checks the wording. With --out, also uses a finished run to find
gates that knocked out candidates who are otherwise strong.
"""
import argparse
import json
import re
from pathlib import Path

# A threshold on a quantity: "3+ years", "at least five years", "10 or more people",
# "minimum of 2 launches". Plain "at least one role" is a fact and does not match.
_NUM = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)"
_UNIT = r"(?:years?|yrs?|months?|people|engineers|reports|launches|customers|employees)"
QUANTITY = re.compile(
    rf"\b{_NUM}\s*\+\s*{_UNIT}|\b(?:at least|minimum of|more than|over)\s+(?:roughly\s+)?{_NUM}\s+{_UNIT}"
    rf"|\b{_NUM}\s+or more\s+{_UNIT}|\b{_NUM}\s+{_UNIT}\s+or more|\broughly\s+{_NUM}\s+or more\s+{_UNIT}",
    re.I)


def bands(question: str) -> list[str]:
    m = re.search(r"(\d+)", question)
    n = int(m.group(1)) if m else 3
    lo, hi = max(1, n // 2), n * 2
    unit = lambda k: f"{k} year" if k == 1 else f"{k} years"  # noqa: E731
    return [f"Under {unit(lo)}", f"{lo} to {unit(n - 1)}" if n - 1 > lo else f"About {unit(lo)}",
            f"{n} to {hi - 1} years", f"{hi} or more years"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rubric", required=True, type=Path)
    ap.add_argument("--out", type=Path, help="a finished run, for data-driven advice")
    ap.add_argument("--strong", type=float, default=0.75, help="strength counted as otherwise strong")
    a = ap.parse_args()
    rubric = json.loads(a.rubric.read_text())
    advice = []

    for mh in rubric.get("must_haves", []):
        text = " ".join([mh.get("question", ""), mh.get("true", ""), mh.get("false", "")])
        if QUANTITY.search(text):
            advice.append({
                "criterion": mh["id"], "now": "hard gate", "recommend": "split: gate + score",
                "why": "it gates on a quantity, so a near miss scores like a flat no",
                "suggest": {
                    "must_have": "Keep a yes/no gate only on the underlying fact (does the resume show "
                                 "this kind of experience at all?), or drop the gate.",
                    "scored": {"id": f"{mh['id']}_depth", "weight": 3,
                               "question": mh["question"], "levels": bands(text)}}})
        else:
            advice.append({"criterion": mh["id"], "now": "hard gate", "recommend": "keep gate",
                           "why": "it asks about a fact a candidate either has or lacks"})
    for sc in rubric.get("scored", []):
        advice.append({"criterion": sc["id"], "now": f"score (weight {sc.get('weight', 1)})",
                       "recommend": "keep score",
                       "why": "partial credit is right unless lacking it entirely disqualifies"})

    if a.out:
        res = json.loads((a.out / "results.json").read_text())
        people = [c for c in res["candidates"] if c.get("must_haves")]
        for item in advice:
            if item["now"] != "hard gate":
                continue
            k = item["criterion"]
            sunk = [c for c in people if c["must_haves"].get(k, 1) < 0.35 and c.get("strength", 0) >= a.strong]
            near = [c for c in people if 0.1 <= c["must_haves"].get(k, 1) < 0.65]
            item["run_evidence"] = (f"{len(sunk)} of {len(people)} candidates scored {a.strong:.0%}+ on "
                                    f"everything else but fell below 0.35 on this gate; {len(near)} sit in "
                                    f"the uncertain 0.10-0.65 band")
            if len(sunk) >= max(2, len(people) // 20) and item["recommend"] == "keep gate":
                item["recommend"] = "review gate"
                item["why"] += "; but the run shows it removing many otherwise-strong candidates"
    print(json.dumps(advice, indent=2))


if __name__ == "__main__":
    main()
