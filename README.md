# jbp-plugins

A Claude Code plugin marketplace. Each folder in `plugins/` is one installable plugin.

## Install

```
/plugin marketplace add <this repo or folder>
/plugin install <plugin-name>@jbp-plugins
```

## Plugins

| Plugin | What it does |
| --- | --- |
| [`jev-resume-screener`](plugins/jev-resume-screener/README.md) | Screens and ranks resumes against a job description with TypeSafe Jev: fit ranking, copied-resume clusters, JD-mirror flags, and a human review queue. |

## Adding a plugin

1. Create `plugins/<name>/` with `.claude-plugin/plugin.json` and its `skills/`, `commands/`, or `agents/`.
2. Add an entry to `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .` and commit.
