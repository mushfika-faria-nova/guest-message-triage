# Decisions

**Who this is for:** reviewers, and anyone asking "why does it work this way?"

To change a decision, don't edit its row. Add a new row that replaces it, and mark the old one "Replaced by N".

| # | Problem | What we picked | What we get | Why not other ways | Cost | Status |
|---|---|---|---|---|---|---|
| 1 | Which language and framework for the service | Python with FastAPI and Pydantic | One Pydantic model gives request validation and the output schema for Claude | Spring Boot: I know it well, but this project is also for learning Python | Python is newer to me, so review takes longer | Accepted |
| 2 | How to manage Python versions and dependencies | uv | One tool for the Python version, the environment and a lockfile | pip + venv: more steps, no lockfile by default. Poetry: slower, needs Python installed separately | One more tool for contributors to install | Accepted |
| 3 | Status code for invalid input | 422, FastAPI's default | Same behaviour on every endpoint, no extra code | 400 (Spring's default): would need a custom exception handler | Clients used to 400 have to handle 422 | Accepted |
| 4 | A message can report more than one problem ("towels missing and the wifi is down") | Return a list of tickets, one per problem | Each problem goes to the right person and is tracked on its own | One ticket marked for review: simpler, but a person has to split it by hand | The API returns a list; the eval has to match tickets to labels; storage needs one row per ticket | Accepted |
| 5 | Internet problems had no category, and they are a common rental complaint | Add an `internet` category | Wifi problems are not pushed into `other` | Leave them in `other`: hides a frequent kind of problem | One more value to label in the eval set | Accepted |
| 6 | The flag `needs_human` was easy to read as "a person must fix this" | Rename it to `needs_review`: a person must read the original message | The name says what to do. Claude reads field names too, so a clear name helps the model | `unclear`: says why, but not what to do | None | Accepted |
| 7 | Claude returned no tickets and no review for "hi", so the message would be lost | A rule in code: no tickets means `needs_review` is true, whatever the model said | The rule always holds and has a test | Fix it in the prompt only: works most of the time, but a prompt is not a guarantee | Messages like "thanks" also go to a person | Accepted |

## Details for developers

- **3.** To change it later, add an exception handler for `RequestValidationError`.
- **4.** The reply is `TriageResult(tickets: list[Ticket], needs_review: bool)`. Structured outputs need an object at the top level, so the list is wrapped. The list is empty when there is nothing to act on ("hi").
- **7.** In `triage()` after the model call. Proven by `tests/test_triage.py::test_no_tickets_always_goes_to_review`, which fails when the rule is removed.
