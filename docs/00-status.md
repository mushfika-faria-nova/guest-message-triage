# Status

**Who this is for:** anyone who wants to know where this project stands, without reading the code.
**After reading:** you know what works today, what's being built, what's next, and what is still undecided.

Last updated: 2026-11-13 · Size: Small · Current phase: 1 of 6, skeleton

## Where it stands

| Phase | What it delivers | Status | Issue / PR |
|---|---|---|---|
| 1 | FastAPI skeleton: health check, `POST /messages` with input validation, tests | ✅ done | first commit |
| 2 | Claude call: message → structured ticket, "needs a human" for unclear messages | ⬜ not started | |
| 3 | Save tickets in Postgres | ⬜ not started | |
| 4 | Eval set and cost per message | ⬜ not started | |
| 5 | Production basics: Dockerfile, structured logs, CI | ⬜ not started | |
| 6 | Bulk mode (Message Batches API) and one agent step with two tools | ⬜ not started | |

## What works today
- `GET /health` returns `{"status": "ok"}` (test passes)
- `POST /messages` accepts 1 to 2000 characters of text and rejects empty or missing text with 422 (3 tests pass)

## In progress
Nothing yet. Phase 2 is next.

## Next
Phase 2: the Claude call with a Pydantic output model.

## Open decisions
- Which model is the default (Haiku or Sonnet). Decided by the eval in phase 4, on accuracy and cost.

## Backlog
None yet.

## Not built yet / known limits
- No Claude call yet: `POST /messages` only echoes the text and its length.
- No storage, no auth, no Docker.
