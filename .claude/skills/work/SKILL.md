---
name: work
description: Work a GitHub issue end to end - design, wait for approval, implement on a branch, test locally, review, open a PR. Never merges.
argument-hint: <issue-number>
disable-model-invocation: true
---

Work GitHub issue #$ARGUMENTS.

## 1. Start clean

- `git status` must be clean and you must be on `main`. If not, stop and ask — don't stash.
- `git pull --ff-only`.
- `gh issue view $ARGUMENTS --comments`. State the title and, in a sentence, what is actually being
  asked. If the issue is ambiguous, or bundles more than one unit of work, say so now.

## 2. Design, then stop

Read `CLAUDE.md`, `DESIGN.md` and the code the change touches. Draft a short design:

```
## Design for #<n>: <title>
**Change:** <what changes in the code, in a few bullets>
**Lines:** ~<n> added to app/ (<total after> / 200)
**Verify:** <the smoke.py assertion(s) and any manual check>
**DESIGN.md:** <unchanged, or what decision changes and why>
**Out of scope:** <things deliberately not done>
```

Run the `architect` agent on the draft. Fix what it rightly raises; say which findings you dropped
and why.

Then show the design to the user and **stop. Write no code until the user approves.**

Once approved, post the final design — including any changes the user asked for — as an issue
comment: write it to a temp file in the scratchpad, then `gh issue comment $ARGUMENTS --body-file <file>`.

## 3. Implement

- `git checkout -b issue-$ARGUMENTS-<short-slug>`
- Implement exactly the approved design. If it turns out to need more, stop and tell the user — a
  separate issue is usually the answer.
- Add or update `tests/smoke.py` assertions for the acceptance criteria.
- Update `README.md` only for user-visible changes (endpoints, config, how to run). Update
  `DESIGN.md` if a recorded decision changed.

## 4. Test locally

Run every check that applies (skip the ones whose files don't exist yet, and say so):

1. `ruff check .`
2. The line-budget command from `CLAUDE.md` — must be under 200.
3. Start the service, run `python tests/smoke.py`, stop the service.
4. `docker build .` if `Dockerfile` or `requirements.txt` changed and Docker is available.

If a check fails twice for the same reason, stop and report — don't grind.

## 5. Review

Run the `reviewer` agent with the issue number. Triage the findings yourself: fix the real ones, and
list the ones you dropped with a reason. Re-run the checks after fixes.

If review raises more than about five real problems, the change is probably too big — stop and
discuss with the user.

## 6. Commit and open the PR

- Tidy the history: each commit makes sense on its own, short imperative messages, no "wip" commits.
- `git push -u origin HEAD`
- Write the PR body with the `pr` skill, then `gh pr create --title "<title>" --body-file <file>`.
- Report the PR URL and **stop**. Never merge — the user reviews and merges.
