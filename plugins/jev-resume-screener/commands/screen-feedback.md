---
description: Review screener results with me, ask why we disagreed, and log lessons for future runs
argument-hint: "[optional: path to the run folder]"
---

Use the jev-resume-screener skill's step 7 ("Learn from the reviewer"). Its
scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/jev-resume-screener/scripts`; run
them through `run.sh`. The run folder is $ARGUMENTS if I gave one; otherwise ask.

Ask for my advance / maybe / reject decisions, compare them with
`feedback.py compare`, then ask me about each disagreement and one overall
question about what to weigh differently. Recommend gate-versus-score changes
where a gate sank candidates I liked. Log only the lessons I confirm, with
`feedback.py log`, and tell me where the log is.
