# Status

**Who this is for:** anyone who wants to know where this project stands, without reading the code.
**After reading:** you know what works today, what's being built, what's next, and what is still undecided.

Last updated: 2026-11-14 · Size: Small · Current phase: 3 of 6, Postgres

## Where it stands

| Phase | What it delivers | Status | Issue / PR |
|---|---|---|---|
| 1 | FastAPI skeleton: health check, `POST /messages` with input validation, tests | ✅ done | first commit |
| 2 | Claude call: message → one ticket per problem, unclear messages marked for review | ✅ done | PR #1 |
| 3 | Save messages and tickets in Postgres | 🔄 in progress | branch `feat/postgres` |
| 4 | Eval set and cost per message | ⬜ not started | |
| 5 | Production basics: failure handling, Dockerfile, structured logs, CI | ⬜ not started | |
| 6 | Bulk mode (Message Batches API) and one agent step with two tools | ⬜ not started | |

## What works today
- `GET /health` returns `{"status": "ok"}` (test passes)
- `POST /messages` rejects empty or missing text with 422, without calling Claude and without saving anything (3 tests pass)
- `POST /messages` returns one ticket per problem, using Claude structured output (tested with a fake client; tried by hand on 4 messages)
- A message with no tickets always goes to review (test passes, and fails when the rule is removed)
- The message and its tickets are saved in Postgres in one transaction (test against a real test database passes, and fails when the save is removed)
- Tables are created by an Alembic migration; `alembic check` shows the models and the database match

## In progress
Phase 3: review and merge `feat/postgres`.

## Next
Failure handling: what the API returns when Claude is down, rate-limited, cuts off its reply or returns invalid output, and keeping the message when that happens.

## Open decisions
- Which model is the default (Haiku or Sonnet). Decided by the eval in phase 4, on accuracy and cost.
- Whether `POST /messages` returns 201 with the saved message id. Today it returns 200 with the tickets only.

## Backlog
None yet.

## Not built yet / known limits
- No eval yet: how often Claude is right is not measured. Hand tries only.
- No handling yet for refusals, cut-off replies or API errors. If Claude fails, the request fails and the message is not saved.
- No auth, no Docker image for the service, no CI.
- Ids are 4-byte integers (about 2.1 billion rows). Enough here; a real system would use `bigint`.
