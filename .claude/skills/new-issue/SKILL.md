---
name: new-issue
description: Turn a goal into one or more GitHub issues, each a single unit of work. Interviews the user briefly first, then proposes the breakdown and creates the issues only after approval.
argument-hint: <goal, or a DESIGN.md section to break down>
disable-model-invocation: true
---

Turn this goal into GitHub issues: $ARGUMENTS

## 1. Understand it

Read `CLAUDE.md`, `DESIGN.md`, the code under `app/` and the open issues (`gh issue list`). Look up
facts yourself; only ask the user for **decisions**.

If anything about the goal is unclear, interview the user in rounds. Number each question, give your
recommended answer, and word it so "yes" accepts the recommendation:

```
❓ **Q1 - <title>**: <question>

➡️ <recommended answer>
```

Ask only the questions whose prerequisites are settled. Stop when nothing is left to assume.

## 2. Slice into units of work

Each issue is **one unit of work**: a single behaviour you can describe in one sentence, that can
be demonstrated on its own through the API (usually a new `tests/smoke.py` assertion).

- Slice vertically: each issue delivers working behaviour end to end, not "write the models" then
  "write the endpoint".
- Put setup or prefactoring first, if a later issue needs it.
- Estimate the Python lines each issue adds to `app/`. The total must stay under 200 — if the plan
  doesn't fit, say so now and suggest what to cut (DESIGN.md lists cut candidates).
- Record which issues block which.

## 3. Check with the user

Show the breakdown as a numbered list: title, one-sentence behaviour, estimated lines, blocked by.
Ask whether any issues should be merged or split. Iterate until approved. **Create nothing before
approval.**

## 4. Create the issues

Create them in dependency order (blockers first), so later issues can reference real numbers:

```
gh issue create --title "<title>" --body-file <tmpfile>
```

Write the body to a temp file in the scratchpad (avoids shell-quoting problems on Windows and Linux).
Body template:

```markdown
## What
<the behaviour, from the API user's point of view — one or two sentences>

## Acceptance criteria
- [ ] <observable through the API, e.g. "POST /ingest with a blocklisted domain returns verdict BAD, source blocklist">
- [ ] `tests/smoke.py` covers it
- [ ] Python in `app/` still under 200 lines

## Notes
<relevant DESIGN.md section, constraints, estimated lines>

## Blocked by
<#n, or "None">
```

No file paths or code in issues — they go stale. Report the created issue numbers and links.
