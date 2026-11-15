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
| 8 | What to store | Two tables: `messages` (with the original text) and `tickets`, linked by `message_id` | A person handling `needs_review` can read the original. One message, many tickets (decision 4) fits a foreign key | Tickets only: smaller, but the original text is lost. One table with JSON tickets: harder to query by category or urgency | The guest's text is stored, so it is personal data in a real system | Accepted |
| 9 | When to save | After Claude answers, message and tickets in one transaction | Never a message without its tickets | Save the message first, then update it: two writes, and a half-finished row if Claude fails | If Claude fails, the message is not saved (phase 5 changes this) | Accepted |
| 10 | Column type for `category` and `urgency` | Plain text; Pydantic checks the values | A new category needs no migration | A Postgres enum: the database checks the values too, but every new value needs a migration | Bad values written outside the API are not stopped by the database | Accepted |
| 11 | How to test saving | A real Postgres test database (`triage_test`), Claude faked | The test proves rows land, with the foreign key and NOT NULL rules | A fake session: only proves `add()` was called. SQLite: different SQL dialect | Tests need Docker running | Accepted |
| 12 | Claude's reply is cut off, refused or doesn't match the schema | No tickets, `needs_review` true. Anything but `stop_reason == "end_turn"` is not trusted, even if tickets were parsed | A bad reply never becomes a wrong ticket | Retry the call: costs again and a refusal or cut-off usually repeats. Keep the parsed tickets after a refusal: they may be wrong | A person reads these messages | Accepted |
| 13 | What the API does when Claude can't be reached after the SDK's 2 retries | Save the message with `needs_review` true and return 200 | The message is never lost, and the client has nothing to retry | 503 with Retry-After: the message isn't saved, and a client retry can save it twice | An outage looks like a busy review queue, so it must be caught from the logs (`warning` for temporary errors, `error` for the rest) | Accepted |
| 14 | How long to wait for Claude | 30 s timeout, 2 retries (the SDK default is 10 minutes) | A stuck call fails in about 90 s at worst, not 30 minutes | No retries: fails on every short blip | A very slow but valid reply is cut off and goes to review | Accepted |

## Details for developers

- **3.** To change it later, add an exception handler for `RequestValidationError`.
- **4.** The reply is `TriageResult(tickets: list[Ticket], needs_review: bool)`. Structured outputs need an object at the top level, so the list is wrapped. The list is empty when there is nothing to act on ("hi").
- **7.** In `triage()` after the model call. Proven by `tests/test_triage.py::test_no_tickets_always_goes_to_review`, which fails when the rule is removed.
- **8.** Models in `src/guest_message_triage/db.py`, schema in `migrations/versions/`. Postgres doesn't index foreign keys on its own, so `tickets.message_id` has an index.
- **9.** `save_triage()` in `db.py` adds the message with its tickets and commits once. One session per request comes from the `get_session` dependency.
- **11.** `tests/conftest.py` builds the tables with `create_all` and empties them after each test. `TEST_DATABASE_URL` can point the tests at another database (CI). `test_message_and_tickets_are_saved` fails when the save call is removed.
- **12.** In `triage()`: `parse()` validates inside the call, so a cut-off reply raises `ValidationError` there; the `stop_reason` check comes after. `review_only()` builds the result. Proven by `test_cut_off_reply_goes_to_review` and `test_refusal_goes_to_review_even_with_tickets`.
- **13.** In `create_message()`. `EnforcedSpendLimitReachedError` is a subclass of `RateLimitError` but does not clear by itself, so it is caught first and logged as `error`. Proven by `test_claude_failure_saves_message_for_review` (connection error, 500, spend limit, 401) and `test_spend_limit_is_logged_as_error_not_as_temporary`; both fail when their code is removed.
