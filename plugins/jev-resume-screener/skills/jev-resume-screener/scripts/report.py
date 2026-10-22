#!/usr/bin/env python3
"""Build report.html from results.json (and optionally merge rationales).

  python report.py --out ./run1
  python report.py --out ./run1 --rationales ./run1/rationales.json

rationales.json: {"C0003": "One or two sentences on why...", ...}
"""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json  # noqa: E402

CSS = """
:root{--bg:#fbfaf7;--card:#fff;--ink:#1f1e1b;--muted:#6b6963;--line:#e4e1d8;
--good:#0f6e56;--goodbg:#e1f5ee;--warn:#854f0b;--warnbg:#faeeda;--bad:#a32d2d;--badbg:#fcebeb;
--acc:#534ab7;--accbg:#eeedfe;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#1c1b19;--card:#262522;--ink:#ecebe6;--muted:#a3a19a;
--line:#3a3935;--good:#9fe1cb;--goodbg:#08504133;--warn:#fac775;--warnbg:#63380633;--bad:#f7c1c1;
--badbg:#791f1f33;--acc:#cecbf6;--accbg:#3c348933;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:1180px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:24px;margin:0 0 4px;font-weight:600}h2{font-size:18px;margin:36px 0 10px;font-weight:600}
.sub{color:var(--muted);margin:0 0 20px}
.banner{background:var(--badbg);color:var(--bad);padding:10px 14px;border-radius:8px;margin:0 0 18px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.stat b{display:block;font-size:22px}.stat span{color:var(--muted);font-size:13px}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:0}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;margin:0 4px 4px 0;white-space:nowrap}
.g{background:var(--goodbg);color:var(--good)}.w{background:var(--warnbg);color:var(--warn)}
.b{background:var(--badbg);color:var(--bad)}.a{background:var(--accbg);color:var(--acc)}
.fit{font-weight:600;font-size:16px}.muted{color:var(--muted);font-size:13px}
.why{font-size:13px;margin-top:4px;max-width:420px}
footer{margin-top:40px;color:var(--muted);font-size:13px}
"""


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def prob_pill(label, p):
    cls = "g" if p >= 0.65 else "w" if p >= 0.35 else "b"
    return f'<span class="pill {cls}">{esc(label)} {p:.0%}</span>'


def build_report(out: Path, rationales: dict | None = None) -> Path:
    out = Path(out)
    data = load_json(out / "results.json")
    if rationales:
        for c in data["candidates"]:
            if c["id"] in rationales:
                c["rationale"] = rationales[c["id"]]
        save_json(out / "results.json", data)
    cands = data["candidates"]
    ranked = [c for c in cands if c.get("fit_index") is not None]
    review = [c for c in cands if c.get("review")]
    mirrors = [c for c in cands if c.get("mirror", {}).get("flagged")]
    dups = data.get("duplicates", [])
    by_id = {c["id"]: c for c in cands}
    tiers = {t: sum(1 for c in ranked if c["tier"] == t) for t in ("Strong", "Possible", "Unlikely")}

    rows = []
    for c in ranked:
        mh = "".join(prob_pill(k, v) for k, v in c.get("must_haves", {}).items())
        sc = "".join(f'<span class="pill a">{esc(k)} {v["score"]:.1f}/{v["max"]}</span>'
                     for k, v in c.get("scored", {}).items())
        flags = "".join(f'<span class="pill b">{esc(f)}</span>' for f in c.get("flags", []))
        if c.get("review"):
            flags += '<span class="pill w">needs review</span>'
        why = f'<div class="why">{esc(c["rationale"])}</div>' if c.get("rationale") else ""
        rows.append(
            f"<tr><td>{c['rank']}</td><td><b>{esc(c['id'])}</b><div class='muted'>{esc(c['file'])}</div>{why}</td>"
            f"<td class='fit'>{c['fit_index']:.0f}</td><td>{esc(c['tier'])}</td>"
            f"<td>{mh or '<span class=muted>none set</span>'}</td><td>{sc}</td>"
            f"<td>{c['mirror']['evidence']:.0%}</td><td>{flags}</td></tr>")

    dup_rows = []
    for d in dups:
        names = ", ".join(f"{m} ({esc(by_id[m]['file'])})" for m in d["members"])
        dup_rows.append(f"<tr><td><b>{d['cluster']}</b></td><td>{names}</td>"
                        f"<td class='muted'>{'<br>'.join(esc(e) for e in d['evidence'][:4])}</td></tr>")

    mir_rows = [
        f"<tr><td><b>{c['id']}</b><div class='muted'>{esc(c['file'])}</div></td>"
        f"<td>{c['mirror']['overlap']:.0%}</td><td>{c['mirror']['longest_run']} words</td>"
        f"<td>{c['mirror']['jev_mirror']:.0%}</td><td>{c['mirror']['evidence']:.0%}</td>"
        f"<td>{c.get('rank', '')}</td></tr>" for c in mirrors]

    rev_rows = [f"<tr><td><b>{c['id']}</b><div class='muted'>{esc(c['file'])}</div></td>"
                f"<td>{c.get('rank', '—')}</td><td>{'<br>'.join(esc(r) for r in c['review'])}</td></tr>"
                for c in review]

    def table(head, body, empty):
        if not body:
            return f"<p class='muted'>{empty}</p>"
        return ("<div class='wrap'><table><thead><tr>" + "".join(f"<th>{h}</th>" for h in head)
                + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>")

    banner = ("<div class='banner'><b>Mock run.</b> These answers came from an offline stand-in, "
              "not Jev. Use them to test the setup only, never to judge candidates.</div>"
              if data.get("mock") else "")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Screening report: {esc(data.get('role') or 'role')}</title><style>{CSS}</style></head><body><main>
<h1>Screening report: {esc(data.get('role') or 'role')}</h1>
<p class="sub">A sorted reading list, not a decision. Every candidate here still gets a human read.</p>
{banner}
<div class="stats">
<div class="stat"><b>{len(cands)}</b><span>resumes processed</span></div>
<div class="stat"><b>{tiers['Strong']}</b><span>strong fit</span></div>
<div class="stat"><b>{tiers['Possible']}</b><span>possible fit</span></div>
<div class="stat"><b>{len(review)}</b><span>need a human look</span></div>
<div class="stat"><b>{sum(len(d['members']) for d in dups)}</b><span>in copy clusters</span></div>
<div class="stat"><b>{len(mirrors)}</b><span>JD-mirror flags</span></div>
</div>
<h2>Ranked shortlist</h2>
<p class="muted">Fit index = probability all must-haves are met × weighted strength on scored criteria, 0–100. It ranks; it is not a calibrated probability of a good hire.</p>
{table(['#', 'Candidate', 'Fit', 'Tier', 'Must-haves (probability met)', 'Scored criteria', 'Evidence', 'Flags'], rows, 'No candidates scored.')}
<h2>Copy clusters</h2>
<p class="muted">Resumes that match once names and contact details are removed.</p>
{table(['Cluster', 'Members', 'Evidence'], dup_rows, 'No copied resumes found.')}
<h2>JD-mirror flags</h2>
<p class="muted">Heavy verbatim overlap with the job description that Jev also reads as copied. Low evidence makes the flag stronger.</p>
{table(['Candidate', 'JD phrases reused', 'Longest copied run', 'Jev: copied', 'Evidence', 'Rank'], mir_rows, 'No mirror flags.')}
<h2>Human review queue</h2>
{table(['Candidate', 'Rank', 'Why it needs a look'], rev_rows, 'Nothing queued.')}
<footer>Model: {esc(data.get('model'))}{' (mock)' if data.get('mock') else ''} · Jev requests: {data['usage']['requests']} · cached: {data['usage']['cached']} · input tokens: {data['usage']['input_tokens']:,}</footer>
</main></body></html>"""
    path = out / "report.html"
    path.write_text(page, encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rationales", type=Path)
    a = ap.parse_args()
    r = json.loads(a.rationales.read_text()) if a.rationales else None
    print(build_report(a.out, r))
