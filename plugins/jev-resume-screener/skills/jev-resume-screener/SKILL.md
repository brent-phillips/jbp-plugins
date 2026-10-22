---
name: jev-resume-screener
description: Screen and stack-rank a folder of job applicant resumes against a job description using TypeSafe's Jev decision model, flag copied resumes (identical apart from the name) and resumes that mirror the job description's own wording, and route uncertain calls to a human review queue. Use this skill whenever the user wants to sort, rank, triage, shortlist, or screen resumes, CVs, or job applicants, find duplicate or templated resumes, detect AI-tailored resumes, or build a hiring rubric, even if they don't mention Jev.
compatibility: Python 3.10+ (the launcher finds it and installs pypdf and python-docx in a private venv). A TypeSafe API key for real runs; --mock works offline.
---

# Jev resume screener

Claude is the slow thinker: it writes the rubric, runs the pipeline, and
explains the top tier. Jev is the fast thinker: it answers the same narrow
questions about every resume with probabilities. Plain code does anything that
should be exact. A human makes every decision; the output is a sorted reading
list, never a rejection.

Run every script through the launcher, never with a bare `python`:

```bash
S="<this skill's directory>/scripts"
"$S/run.sh" <script.py> [args]
```

## Workflow

### 0. Check the Jev connection
Run `"$S/run.sh" jev_setup.py --check`. On `JEV_STATUS=ok`, continue.
On `missing_key`, tell the user to run this in a normal Terminal window (not
through Claude, which has no keyboard for the hidden prompt) so the key never
passes through the chat:

```bash
"<scripts dir>/run.sh" jev_setup.py --save
```

Never ask the user to paste the key into the conversation, and never write it
anywhere yourself. On `error`, show the message and stop. If they only want to
try the pipeline, offer `--mock`.

### 1. Gather inputs, one question at a time, in this order
1. **The job description.** A file path, or pasted text that you save to
   `<workdir>/job_description.txt`.
2. **Hiring-manager notes.** Anything about what actually matters, what to
   ignore, deal-breakers, or feedback on earlier candidates. "None" is fine.
   Save what they give to `<workdir>/hiring_notes.md`.
3. **The resume folder.** PDF, DOCX, TXT, or MD files. Count them and their
   types before going further. If it is a zip, extract it into a new, empty
   folder; never extract inside Downloads or the source folder.

`<workdir>` is a new folder next to the resumes named `screen-YYYY-MM-DD`,
unless the user names one. Keep it out of git repositories and synced vaults:
it holds candidate data.

If the user hasn't said so, confirm they're allowed to send candidate resumes
to a third-party API under their employer's policies. Names and contact details
are stripped before anything leaves the machine, but work history is not.

### 2. Draft the rubric with the user
First read what earlier reviews taught: `"$S/run.sh" feedback.py show --role "<role>"`.
Then read `references/rubric-guide.md` and draft `<workdir>/rubric.json` from the
job description and the hiring notes, using `assets/rubric.example.json` as the
template: 2 to 4 must-haves, 3 to 6 weighted scored criteria. Hiring notes
outrank the JD where they conflict.

Check every criterion with `"$S/run.sh" rubric_check.py --rubric <workdir>/rubric.json`.
It says, per criterion, whether it should be a hard gate or a weighted score.
Gates are for facts a candidate has or lacks; quantities where close still counts
(years of experience is the usual one) become scored bands. Rewrite any
suggested scored question as a "how many / how much" question.

Show the user the rubric in plain language (not JSON), with the gate-or-score
call for each criterion and any logged lessons that apply. Propose each change a
lesson implies and let the user accept or reject it; never apply a lesson
silently. Keep every question job-related; the guide lists what never goes in a
rubric.

### 3. Calibrate on a small set (recommended, first run for a role)
Have the recruiter label 10 to 20 resumes yes / maybe / no in `labels.csv`
(columns `file,label`) before seeing any scores. Then:

```bash
"$S/run.sh" screen.py --resumes <calib_folder> --jd <jd.txt> --rubric rubric.json --out <workdir>/calib
"$S/run.sh" calibrate.py --out <workdir>/calib --labels labels.csv
```

Under ~80% pairwise agreement: read the disagreements, propose specific rubric
edits, rerun. Unchanged requests come from cache at no cost.

### 4. Full run

```bash
"$S/run.sh" screen.py --resumes <folder> --jd <jd.txt> --rubric <workdir>/rubric.json --out <workdir>/run
```

For more than ~25 resumes, tell the user the count first; a run uses roughly
2,200 Jev input tokens per resume. Use `--mock` to test setup without spending
credits. Mock answers are keyword overlap, not Jev; never present them as
judgments.

### 5. Write rationales for the top tier
Read `run/results.json`. For the top 10 (or the Strong tier, if smaller) and
anything in the review queue the user asks about, read the redacted resume in
`run/redacted/<id>.txt` and write one or two sentences per candidate: the
strongest evidence for fit and the biggest open question for the interview.
Refer to candidates by ID, not name. Save as `run/rationales.json`
(`{"C0003": "..."}`) and run:

```bash
"$S/run.sh" report.py --out <workdir>/run --rationales <workdir>/run/rationales.json
```

### 6. Hand back
Give the user `run/report.html` and `run/results.csv`. Summarize in a few
lines: how many are Strong / Possible, how many need a human look and why,
copy clusters found, mirror flags, authenticity notes. Remind them the fit index ranks; it is not a
calibrated probability of a good hire. Offer the review step next.

### 7. Learn from the reviewer
Once the reviewer has read the report, ask for their decisions: advance, maybe,
or reject for each candidate they looked at, with a short note where they
disagree. Save them as `<workdir>/run/decisions.csv` (columns
`file,decision,note`) and run:

```bash
"$S/run.sh" feedback.py compare --out <workdir>/run --decisions <workdir>/run/decisions.csv
```

Ask about each disagreement, one at a time, using the evidence the comparison
prints: "The screener had C0012 as Unlikely because the management gate scored
0.14; you'd advance them. What did you see that it missed?" Then ask one overall
question: what should the screener weigh differently next time? If the output
has `gate_advice`, run `rubric_check.py --rubric <rubric> --out <workdir>/run`
and recommend turning that gate into a score.

Write each lesson the reviewer confirms to a JSON file and log it:

```bash
"$S/run.sh" feedback.py log --out <workdir>/run --entry <entry.json>
```

An entry is `{"lesson": "...", "rubric_change": "...", "scope": "role",
"candidates": [{"id": "C0012", "reviewer": "advance", "screener": "Unlikely",
"why": "..."}]}`; use `"scope": "general"` for lessons that apply to every role.
Lessons cite candidate IDs, never names. The log lives in
`~/.jev-screener/learnings/`, outside any repository; step 2 reads it next time.

## How to read the flags

- **Copy cluster**: two or more resumes that match after names and contacts
  are removed (shingle similarity ≥ 0.90, or 0.55–0.90 and Jev confirms the
  copy). Often a template, a resume mill, or one person applying under several
  names. Worth a look, not proof of fraud.
- **JD mirror**: the resume reuses a large share of the job description's
  phrases verbatim (or contains a long copied run) *and* Jev reads the wording
  as copied. Low evidence score strengthens the signal. Many honest candidates
  tailor resumes to postings; the flag means "verify in the interview," not
  "reject." Light paraphrasing of the JD is not reliably caught.
- **Authenticity**: the resume's own timeline or claims don't hold together.
  Code checks overlapping full-time roles, a degree dated years after the first
  job, title jumps that skip most of the ladder, very short senior tenures,
  "N years of <tool>" beyond the tool's age, and very long certification lists.
  Jev judges whether claimed results are plausible for the roles. Heavy stock
  phrasing ("best-in-class", "cutting-edge") is reported as a weak signal. Each
  note says what to verify; there are innocent explanations for all of them
  (concurrent part-time roles, degrees finished while working, startup titles).
  Employment gaps are never checked.
- **Needs review**: a must-have probability between 0.35 and 0.65, a
  low-confidence score, a flag, or a short extraction (often a scanned PDF).

## Scripts

| Script | Does |
| --- | --- |
| `scripts/run.sh` | Launcher: finds Python 3.10+, private venv, runs a script |
| `scripts/jev_setup.py` | Check the Jev key and connection, or save a key (hidden input) |
| `scripts/screen.py` | Full pipeline: ingest + redact, dedupe, Jev evaluation, rank, outputs |
| `scripts/report.py` | Rebuild `report.html`; merge rationales |
| `scripts/calibrate.py` | Compare recruiter labels to the ranking |
| `scripts/feedback.py` | Learning loop: compare reviewer decisions, log lessons, show them next run |
| `scripts/rubric_check.py` | Recommend hard gate or weighted score for each criterion |
| `scripts/benchmark.py` | Score a run against a labeled answer key (testing the screener itself) |
| `scripts/jev_client.py` | Jev API client: caching, retries, parallel calls, mock mode |
| `scripts/authenticity.py` | Timeline and claim checks (local, exact) |
| `scripts/common.py` | Extraction, redaction, text similarity |
