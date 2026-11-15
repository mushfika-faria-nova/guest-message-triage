# Status

**Who this is for:** anyone who wants to know where this project stands, without reading the code.
**After reading:** you know what works today, what's being built, what's next, and what is still undecided.

Last updated: 2026-11-15 · Size: Small · Current phase: 5 of 6, production basics

## Where it stands

| Phase | What it delivers | Status | Issue / PR |
|---|---|---|---|
| 1 | FastAPI skeleton: health check, `POST /messages` with input validation, tests | ✅ done | first commit |
| 2 | Claude call: message → one ticket per problem, unclear messages marked for review | ✅ done | PR #1 |
| 3 | Save messages and tickets in Postgres | ✅ done | PR #2 |
| 4 | Eval set and cost per message | ⬜ not started | |
| 5 | Production basics: failure handling, Dockerfile, structured logs, CI | 🔄 in progress (failure handling) | branch `feat/failure-handling` |
| 6 | Bulk mode (Message Batches API) and one agent step with two tools | ⬜ not started | |

## What works today
- `GET /health` returns `{"status": "ok"}` (test passes)
- `POST /messages` rejects empty or missing text with 422, without calling Claude and without saving anything (3 tests pass)
- `POST /messages` returns one ticket per problem, using Claude structured output (tested with a fake client; tried by hand on 4 messages)
- A message with no tickets always goes to review (test passes, and fails when the rule is removed)
- The message and its tickets are saved in Postgres in one transaction (test against a real test database passes, and fails when the save is removed)
- Tables are created by an Alembic migration; `alembic check` shows the models and the database match
- A cut-off, refused or invalid Claude reply goes to review instead of becoming a ticket (2 tests)
- If Claude can't be reached, is rate-limited, rejects the key or the spend limit is hit, the message is still saved for review and the API returns 200 (4 cases tested; spend limit logged as an error, tested)

## In progress
Phase 5: failure handling (branch `feat/failure-handling`). Phase 4 (eval) comes after it.

## Next
Phase 4: eval set of labelled synthetic messages, accuracy per field, cost per message.

## Open decisions
- Which model is the default (Haiku or Sonnet). Decided by the eval in phase 4, on accuracy and cost.
- Whether `POST /messages` returns 201 with the saved message id. Today it returns 200 with the tickets only.

## Backlog
None yet.

## Not built yet / known limits
- No eval yet: how often Claude is right is not measured. Hand tries only.
- An outage only shows in the logs (the API still returns 200). Logs are plain text; structured logs and alerts come later in phase 5.
- If the database is down, the request fails with 500 and the message is lost.
- No auth, no Docker image for the service, no CI.
- Ids are 4-byte integers (about 2.1 billion rows). Enough here; a real system would use `bigint`.
