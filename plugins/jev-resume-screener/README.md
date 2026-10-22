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

- `/jev-setup` connects your TypeSafe key. You type the key into a hidden prompt;
  it is saved to `~/.typesafe/api_key` and never passes through the chat.
- `/screen-resumes` asks for the job description, hiring-manager notes, and the
  resume folder, then drafts a rubric with you and runs the screen.

Needs Python 3.10+. The first run builds a private environment in
`~/.jev-screener/venv` with `pypdf` and `python-docx`.

## Known limits (from a 100-resume labeled benchmark)

- Copied resumes: 15/15 caught. Heavy JD mirroring: 9/9.
- Light JD paraphrasing: not caught.
- Authenticity problems (degree dated after first job, overlapping roles,
  inflated claims): no dedicated check yet.
