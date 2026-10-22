#!/usr/bin/env python3
"""Compare the recruiter's own judgments with the screener's ranking.

  python calibrate.py --out ./calib --labels labels.csv

labels.csv has two columns, file and label, where label is yes, maybe, or no:
  file,label
  jane_doe.pdf,yes
  resume_17.docx,no

Prints how often the screener orders a pair of resumes the same way the
recruiter did, and lists the biggest disagreements so Claude can propose
rubric changes. Aim for 80%+ agreement before running the full stack.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

RANK = {"yes": 2, "maybe": 1, "no": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--labels", required=True, type=Path)
    a = ap.parse_args()

    data = json.loads((a.out / "results.json").read_text())
    by_file = {c["file"]: c for c in data["candidates"] if c.get("fit_index") is not None}
    labels = {}
    with open(a.labels, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lab = row["label"].strip().lower()
            if lab in RANK and row["file"] in by_file:
                labels[row["file"]] = lab
    if len(labels) < 3:
        sys.exit("Need at least 3 labeled resumes that were scored in this run.")

    files = list(labels)
    agree = total = 0
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            a_, b_ = files[i], files[j]
            if RANK[labels[a_]] == RANK[labels[b_]]:
                continue
            total += 1
            human = RANK[labels[a_]] > RANK[labels[b_]]
            model = by_file[a_]["fit_index"] > by_file[b_]["fit_index"]
            agree += human == model
    print(f"Labeled resumes: {len(labels)}")
    for lab in ("yes", "maybe", "no"):
        fits = [by_file[f]["fit_index"] for f in files if labels[f] == lab]
        if fits:
            print(f"  avg fit index for '{lab}': {sum(fits) / len(fits):.1f}  (n={len(fits)})")
    if total:
        print(f"Pairwise agreement: {agree}/{total} = {agree / total:.0%}")

    print("\nBiggest disagreements (review these with Claude):")
    yes_low = sorted((f for f in files if labels[f] == "yes"), key=lambda f: by_file[f]["fit_index"])
    no_high = sorted((f for f in files if labels[f] == "no"), key=lambda f: -by_file[f]["fit_index"])
    for f in yes_low[:3] + no_high[:3]:
        c = by_file[f]
        print(f"  {f}: you said {labels[f]}, fit {c['fit_index']:.0f}, "
              f"must-haves {c.get('must_haves')}, scores "
              f"{ {k: v['norm'] for k, v in c.get('scored', {}).items()} }")


if __name__ == "__main__":
    main()
