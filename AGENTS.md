# Agent instructions for the Facilities project

## Before editing

- Read the assigned task and its acceptance check in [D1-After-Hours-Tasks.md](D1-After-Hours-Tasks.md). Use the requirement and task IDs in work logs and review notes.
- Run the task's check before implementation and record the result. For a missing feature, confirm that the check fails for the expected reason.
- Keep changes within the assigned task. Preserve existing request data, status rules, and access boundaries.

## Code and verification

- `app.py` contains the local WSGI demo. Derive the acting user and role from the server-side session.
- `after_hours.py` contains the SQLite service. Scope student reads and writes to the owner. Save status changes, audit entries, and associated notifications together when the task requires them. Preserve existing databases when changing the schema.
- The Python application uses the standard library. Tests use pytest and synthetic data. Run commands from the repository root.

| Action | Command |
| --- | --- |
| Start the local demo | `python3 app.py` |
| Check the browser workflow and its service | `python3 -m pytest -q tests` |
| Check all implemented After-Hours services and the demo | `python3 -m pytest -q tests acceptance/ah_t*.py` |

The assigned check and existing regression checks must pass before the change is ready for review. If a check is wrong, report the evidence to the human reviewer. Preserve the test and its assertions during implementation.

## Lab 6 controls

- Run the Lab 6 loop in Docker with the Lab 6 code, Gemini adapter, and launcher mounted read-only. Give the agent a separate writable working copy containing the task files and tests.
- `lab6_after_hours.py` sends the task spec and selected test to the model. Give Lab 6 any relevant instructions from this file explicitly. The launcher builds its context from selected files.
- **Allow** listing files, reading task files, and running pytest through the provided tool.
- **Ask** for human approval before a write. The launcher permits approved writes to the assigned `after_hours.py` or `app.py`. Backlog service tasks use approved exact-snippet edits to `after_hours.py`.
- **Deny** all other tools and writes, including acceptance test edits and arbitrary shell commands. Use only synthetic or anonymized data. Keep API keys, credentials, tokens used for authentication, and personal information out of prompts, output, files, and Git.
- The Lab 6 defaults are 12 steps and a $0.25 estimated-cost threshold per run. The meter uses `PRICE_IN` and `PRICE_OUT` in dollars per million tokens. It checks usage after API calls, so the provider can charge for a call that crosses the threshold. The D1 Gemini runs used configured free-tier rates.

## Human review and work log

- The human operator reviews edit requests during the run. A teammate reviews the resulting diff and reruns the checks in the project before merge.
- Add each non-trivial run to [D1-Agent-Work-Log.md](D1-Agent-Work-Log.md) with the date, requirement and task IDs, tool and model, request, review outcome, input and output tokens, configured cost, and one lesson. Include failed attempts and label missing usage and estimated cost accurately.
