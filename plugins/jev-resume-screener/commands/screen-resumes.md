---
description: Screen a folder of resumes against a job description with Jev (asks for the JD, hiring notes, and the resume folder)
argument-hint: "[optional: path to resume folder]"
---

Use the jev-resume-screener skill to screen resumes. Its scripts are in
`${CLAUDE_PLUGIN_ROOT}/skills/jev-resume-screener/scripts`; run them through `run.sh`.

1. Check the Jev connection first (`run.sh jev_setup.py --check`). If no key is
   set, have me run `run.sh jev_setup.py --save` myself; don't ask me for the key.
2. Then ask me, one at a time and in this order:
   1. the job description (a file path, or I'll paste it),
   2. any hiring-manager notes or feedback on what matters ("none" is fine),
   3. where the resume folder lives. If I passed one here, confirm it instead: $ARGUMENTS
3. Follow the skill's workflow from there: draft the rubric with me, offer
   calibration, run, write rationales for the top tier, and hand back the report.
