"""Score a screen.py run against an answer key CSV. Usage: benchmark.py results.json answer_key.csv"""
import csv, json, sys, collections
res = json.load(open(sys.argv[1]))
key = {r["file"] + ".txt": r for r in csv.DictReader(open(sys.argv[2]))}
people = {p["id"]: p for p in res["candidates"]}
lab = lambda p: key[p["file"]]["label"]
out = collections.OrderedDict()

# copies: true groups vs flagged
dup_true = collections.defaultdict(set)
for p in people.values():
    g = key[p["file"]]["duplicate_group"]
    if g: dup_true[g].add(p["id"])
flagged = {p["id"] for p in people.values() if any("copy" in f for f in p["flags"])}
in_dup = set().union(*dup_true.values())
out["copies"] = dict(members_caught=f"{len(in_dup & flagged)}/{len(in_dup)}", false_flags=sorted(key[people[i]['file']]['file'] for i in flagged - in_dup),
                     groups_fully_caught=f"{sum(g <= flagged for g in dup_true.values())}/{len(dup_true)}",
                     missed=sorted(f"{key[people[i]['file']]['file']} ({lab(people[i])})" for i in in_dup - flagged))

# mirror
mir = {i for i, p in people.items() if "mirror" in lab(p)}
mf = {i for i, p in people.items() if "JD mirror" in p["flags"]}
for kind in ("jd_mirror_heavy", "jd_mirror_light"):
    s = {i for i in mir if lab(people[i]) == kind}
    out[kind] = f"{len(s & mf)}/{len(s)}"
out["mirror_false_flags"] = sorted(people[i]["file"] for i in mf - mir)

# authenticity: anything flagged or sent to review
auth = {i for i, p in people.items() if lab(p).startswith("authenticity")}
out["authenticity_flagged_or_review"] = f"{sum(1 for i in auth if people[i]['flags'] or people[i]['review'])}/{len(auth)}"
af = {i for i, p in people.items() if "authenticity" in p["flags"]}
out["authenticity_flagged"] = f"{len(auth & af)}/{len(auth)}"
out["authenticity_by_label"] = {f"{people[i]['file'][7:10]} {lab(people[i])[len('authenticity_flag_'):]}": i in af
                                for i in sorted(auth)}
out["authenticity_false_flags"] = sorted(f"{people[i]['file']} ({lab(people[i])})" for i in af - auth)

# fit on genuine + authenticity resumes (not copies/mirrors)
tier = {"strong": "Strong", "moderate": "Possible", "weak": "Unlikely"}
conf = collections.Counter()
for p in people.values():
    k = key[p["file"]]
    if k["label"] == "genuine":
        conf[(k["expected_fit"], p.get("tier"))] += 1
out["genuine_fit_matrix(expected->tier)"] = {f"{a}->{b}": n for (a, b), n in sorted(conf.items())}
out["genuine_exact_match"] = f"{sum(n for (a, b), n in conf.items() if tier[a] == b)}/{sum(conf.values())}"
out["mirror_tiers"] = dict(collections.Counter(people[i].get("tier") for i in mir))
print(json.dumps(out, indent=1))
