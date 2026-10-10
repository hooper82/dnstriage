# CLAUDE.md

Guidance for Claude Code working in this repository.

## The project

`dnstriage` is a small HTTP service that classifies DNS domains (blocklist → allowlist → cache →
enrichment → LLM) and reports a verdict and its evidence for each domain. It is a **proof of concept**
and a portfolio piece.

The design lives in `DESIGN.md`. Keep it true: if a change alters a decision recorded there, update it in the same PR.

## Hard rules

- **Never merge.** Agents never merge PRs, never push to `main`, never force-push. The user reviews
  and merges every PR.
- **Simplicity beats everything.** Readability and correctness first, then features.
- **200-line budget.** All Python under `app/` must total under 200 lines. `tests/` and `.claude/` do not count. Check with:
  `python3 -c "import pathlib; print(sum(len(p.read_text().splitlines()) for p in pathlib.Path('app').rglob('*.py')))"`
  (Windows: `py` instead of `python3`)
- **In-memory state only.** No database, no migrations. The README notes that a real deployment would need SQLite/Postgres adaptors.
- **Runs on Windows and Linux, locally and in Docker.** No bash-only steps in the run or test path.
  Use `pathlib`, not hard-coded separators.
- **Fake model by default.** Build and test against the fake model (`tests/fake_model.py`), which the
  defaults point at, so nothing needs configuring. Claude (Sonnet 5.5, via the native Anthropic SDK)
  is used only when the user exports `ANTHROPIC_*`/`MODEL_NAME`; never print or commit a key.
- **Dependencies:** plain `pip` with exact pins in `requirements.txt`. Python 3.12. Ask before adding
  any new dependency.

## Way of working

Sequential, one unit of work at a time, on a feature branch (no worktrees).

1. **Goal → issues.** `/new-issue` turns a goal into GitHub issues, one unit of work each.
2. **Issue → design → stop.** `/work <n>` drafts a design, has the `architect` agent check it, and
   **waits for the user's approval**. The approved design, including the user's changes, is posted
   as a comment on the issue.
3. **Code → test locally → review.** Implement, run the checks below, then the `reviewer` agent.
4. **PR.** Push the branch and open a PR with `/pr`. Stop. The user reviews and merges.

**One PR = one unit of work**: a single behaviour you can describe in one sentence (e.g. "look up a
domain's verdict from the blocklist"). If a change grows beyond that, stop and
propose splitting it into another issue.

**Commits:** each one makes sense on its own; short imperative messages ("Add blocklist tier"), no
prefixes, no "wip" or "fix typo" commits — squash those before pushing.
**Branches:** `issue-<n>-<slug>`.

## Commands

Setup and run (Linux / macOS):

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-dev.txt   # ruff, for the checks
python3 tests/fake_model.py &   # fake model on 8001; the service's default endpoint
.venv/bin/python -m uvicorn app.main:app --port 8080
```

Setup and run (Windows PowerShell; no activation needed, so execution policy doesn't matter):

```
py -3.12 -m venv .venv; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r requirements-dev.txt   # ruff, for the checks
Start-Process py tests/fake_model.py   # fake model on 8001, own window
.venv\Scripts\python -m uvicorn app.main:app --port 8080
```

Checks: `ruff check .` (CI runs it too), the line-budget command above,
`python3 tests/smoke.py` (Windows: `py`) against a running service (and `--model-down` with the fake model stopped), and `docker build .` when the Dockerfile or
dependencies change.

Tests are deliberately minimal: `tests/smoke.py` uses only the standard library (`urllib`) to call
the API and check responses — the Python equivalent of a few `curl` commands. No pytest, no mocks.

## Coding guidelines

**Think before coding.** State assumptions. If something is ambiguous, ask. If a simpler approach
exists, say so.

**Simplicity first.** Minimum code that solves the problem. No speculative features, no
abstractions for single-use code, no configurability nobody asked for, no error handling for
impossible cases. Prefer early returns to nesting. If it could be half the lines and just as clear,
rewrite it.

**Surgical changes.** Touch only what the issue needs. Don't reformat or "improve" adjacent code.
Remove only the orphans your change created; mention other dead code rather than deleting it. Every
changed line should trace to the issue.

**Goal-driven.** Turn the issue's acceptance criteria into checks (usually a `smoke.py` assertion)
and loop until they pass.
