---
name: pr
description: Write a pull request body for this repo. Use whenever opening a PR (the work skill calls it).
---

Write the PR body for the current branch. A human will review it, so keep prose short and make the
change easy to see. Look at `git diff main...HEAD` and `git log main..HEAD --oneline` first.

Template:

````markdown
Closes #<n>

## Summary
<one or two sentences: the behaviour this adds or changes>

<optional: the smallest visual that makes the change clear — a call tree, a pseudocode sketch, or a
`diff` of the request flow. Skip it if the diff is already obvious.>

## Evidence
```
<the actual output of `python tests/smoke.py`, trimmed to the relevant lines>
```
<optional: a sample request and response>

## Checks
- Line budget: <n> / 200 Python lines in `app/`
- `ruff check .`: clean
- Docker build: <passed / not affected>

## Notes for the reviewer
<anything worth knowing: a trade-off made, something deliberately left out, a DESIGN.md decision
that changed. Delete the section if there's nothing.>
````

Rules:

- Use the project's own terms from `DESIGN.md` (registrable domain, tier, verdict, degraded).
- Evidence is real command output, never written by hand.
- No marketing tone, no "simply", no lists of files — the diff already shows the files.
