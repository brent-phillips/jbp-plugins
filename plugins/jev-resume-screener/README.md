# Jev resume screener (Claude Code plugin)

Screens a folder of resumes against a job description with TypeSafe's Jev:
fit ranking, copied-resume clusters, JD-mirror flags, and a human review queue.
The output is a sorted reading list for a recruiter, never a rejection.

## Install

```
/plugin marketplace add brent-phillips/jbp-plugins
/plugin install jev-resume-screener@jbp-plugins
```

Then:

- `/jev-setup` connects your TypeSafe key. It gives you one command to run in a
  normal Terminal window, where you type the key into a hidden prompt. The key is
  saved to `~/.typesafe/api_key` and never passes through the chat.
- `/screen-resumes` asks for the job description, hiring-manager notes, and the
  resume folder, then drafts a rubric with you and runs the screen. While
  drafting, it recommends for each criterion whether it should be a hard gate
  or a weighted score, and proposes changes from earlier reviews.
- `/screen-feedback` asks for your advance / maybe / reject calls, asks why
  you disagreed with the screener, and logs the lessons to
  `~/.jev-screener/learnings/` so the next run can apply them (with your OK).

Needs Python 3.10+. The first run builds a private environment in
`~/.jev-screener/venv` with `pypdf` and `python-docx`.

## Benchmark (100 labeled synthetic resumes)

| Check | Result |
| --- | --- |
| Copied resumes | 15/15 caught, 0 false flags |
| Heavy JD mirroring | 9/9 caught, 0 false flags |
| Light JD paraphrasing | 0/6: not caught |
| Fit, genuine resumes (years as weighted scores, not gates) | 43/60 in the expected tier, up from 32/60 with year gates |
| Authenticity (overlaps, degree dates, title jumps, tool ages, cert stuffing, inflated metrics, buzzwords) | 10/10 flagged; 0 of 60 genuine resumes flagged; 3 flags on one buzzword-heavy resume and its two copies |

The authenticity thresholds were tuned on this same set, so expect lower
numbers on real applicants. Every flag routes to human review; none changes
the ranking.
