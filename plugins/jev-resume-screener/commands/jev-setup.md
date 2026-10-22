---
description: Connect the resume screener to TypeSafe Jev (checks for a key, tests the connection)
---

Run `${CLAUDE_PLUGIN_ROOT}/skills/jev-resume-screener/scripts/run.sh jev_setup.py --check`
and tell me the result in one line.

If it reports `missing_key`, tell me to run this myself so the key never goes
through the chat (in Claude Code I can type it after `!`):

`${CLAUDE_PLUGIN_ROOT}/skills/jev-resume-screener/scripts/run.sh jev_setup.py --save`

Get a key at https://typesafe.ai if I don't have one. After I save it, run the
check again. Never ask me to paste the key into the conversation.
