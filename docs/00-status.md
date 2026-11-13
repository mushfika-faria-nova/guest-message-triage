# Status

**Who this is for:** anyone who wants to know where this project stands, without reading the code.
**After reading:** you know what works today, what's being built, what's next, and what is still undecided.

Last updated: 2026-11-13 · Size: Small · Current phase: 2 of 6, Claude call

## Where it stands

| Phase | What it delivers | Status | Issue / PR |
|---|---|---|---|
| 1 | FastAPI skeleton: health check, `POST /messages` with input validation, tests | ✅ done | first commit |
| 2 | Claude call: message → one ticket per problem, unclear messages marked for review | 🔄 in progress | branch `feat/claude-triage` |
| 3 | Save tickets in Postgres | ⬜ not started | |
| 4 | Eval set and cost per message | ⬜ not started | |
| 5 | Production basics: Dockerfile, structured logs, CI | ⬜ not started | |
| 6 | Bulk mode (Message Batches API) and one agent step with two tools | ⬜ not started | |

## What works today
- `GET /health` returns `{"status": "ok"}` (test passes)
- `POST /messages` rejects empty or missing text with 422, without calling Claude (2 tests pass)
- `POST /messages` returns one ticket per problem, using Claude structured output (tested with a fake client; tried by hand on 3 messages)
- A message with no tickets always goes to review (test passes, and fails when the rule is removed)

## In progress
Phase 2: the Claude call and the `/messages` endpoint returning tickets.

## Next
Phase 2: the Claude call with a Pydantic output model.

## Open decisions
- Which model is the default (Haiku or Sonnet). Decided by the eval in phase 4, on accuracy and cost.

## Backlog
None yet.

## Not built yet / known limits
- No eval yet: how often Claude is right is not measured. Hand tries only.
- No handling yet for refusals, cut-off replies or API errors (phase 2, next step).
- No storage, no auth, no Docker.
