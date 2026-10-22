# Writing the rubric

The rubric is the only place judgment enters the pipeline. Jev answers exactly
the questions it is given, so a sloppy question gets a confident, useless answer.

## Schema

```json
{
  "role": "Title shown on the report",
  "must_haves": [
    {"id": "snake_case", "question": "Yes/no question about the resume",
     "true": "What counts as yes", "false": "What counts as no"}
  ],
  "scored": [
    {"id": "snake_case", "weight": 1-5, "question": "How much/how strong ...?",
     "levels": ["lowest", "...", "highest"]}
  ],
  "settings": {"review_band": [0.35, 0.65], "min_confidence": 0.5,
               "tiers": {"strong": 60, "possible": 30}}
}
```

- `must_haves` become Jev **noul** questions (probability of yes, 0 to 1).
- `scored` become Jev **score** questions over ordered levels (2 to 10 levels).
- The JD-mirror and evidence questions are added automatically. Do not add them.

## Rules for good questions

1. **One fact per question.** "Does the resume show 5+ years of PMM at a B2B SaaS
   company?" is three questions. Split it: years, function, industry. Jev runs
   them in parallel, so more atomic questions cost almost nothing.
2. **Keep must-haves few: 2 to 4.** The fit index multiplies their probabilities,
   so each one is a hard gate. Anything that is really "nice to have" belongs in
   `scored`.
3. **Don't gate on a year count the resume has to add up.** Thresholds like
   "3+ years managing" make Jev total date ranges, and a candidate with 2.5
   clear years falls to p≈0.1 and sinks to Unlikely regardless of everything
   else. In a 100-resume benchmark this one gate caused nearly every fit miss.
   Gate on the fact ("has directly managed engineers") and put the depth in a
   weighted `scored` criterion with levels like "under 1 year / 1–3 / 3–5 / 5+".
   On the 100-resume benchmark, making both year counts scored bands raised
   agreement with the labels from 32 to 43 of 60 genuine resumes.
   `rubric_check.py` flags gates like this automatically.
4. **Define true and false.** Spell out edge cases a recruiter would argue about
   (different job titles for the same work, contract roles, adjacent industries).
5. **Make levels observable.** "Led one or two launches end to end" beats "Good".
   Each level should describe something you could point to on the page.
6. **Weight by what the hiring manager would trade for.** 3 = core, 2 = important,
   1 = tiebreaker.
7. **Ask about the resume, not the person.** "Does the resume show..." keeps Jev
   grounded in the text it has.

## Never put these in a rubric

Questions must be job-related. Do not ask about, score on, or proxy for:
age or graduation year, gender, race or ethnicity, national origin, religion,
disability or health, pregnancy or family status, marital status, photos or
appearance, name, address or neighborhood, or employment gaps (gaps often
reflect caregiving, illness, or layoffs). Avoid school prestige unless the role
genuinely requires a specific credential. If the user asks for one of these,
explain why it is left out and offer a job-related alternative (for example,
"currently authorized to work in the US" is a question for the application form,
not for Jev reading a resume).

## Calibration loop

1. Recruiter labels 10 to 20 resumes yes / maybe / no **before** seeing scores.
2. Run the screener on that set (`--limit` or a separate folder).
3. Run `calibrate.py`. Under ~80% pairwise agreement means the rubric is off.
4. For each disagreement, read the must-have probabilities and level scores.
   Usually one of: a must-have is too strict, a question is ambiguous, a level
   description does not match how the recruiter thinks, or a missing criterion.
5. Edit the rubric, rerun (cached answers make unchanged requests free), repeat.
