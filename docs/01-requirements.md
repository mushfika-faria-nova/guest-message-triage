# Requirements: Guest Message Triage

**Who this is for:** developers and reviewers.
**After reading:** you know the problem, what it must do, and which test proves each part. How it works is in [02-design.md](02-design.md).

## Problem
Guests and cleaners report problems in free text, in any form: "AC leaking in 4, guest at 3pm". Someone has to read each message, work out what it is about and how urgent it is, and create a ticket by hand. Urgent problems can wait behind routine ones.

## What it must do

| ID | It must… | Proven by | Phase |
|---|---|---|---|
| R-1 | Accept a message of 1 to 2000 characters and reject empty or missing text, without calling Claude | `tests/test_app.py` (2 tests) | 1 |
| R-2 | Turn a message into one ticket per problem: category, urgency, unit, next action | eval set, accuracy per field | 2 |
| R-3 | Mark unclear messages, and messages with nothing to act on, for a person to review instead of guessing | `tests/test_triage.py`; eval cases with unclear messages | 2 |
| R-4 | Save every message and its tickets; save nothing for rejected input | `tests/test_app.py::test_message_and_tickets_are_saved`, `test_invalid_message_is_not_saved` (real Postgres test database) | 3 |
| R-5 | Record tokens and cost for every message | test on the usage log | 4 |
| R-6 | Triage a file of hundreds of messages in one run, with the total cost of the run | run on a synthetic CSV, results matched to inputs | 6 |
| R-7 | Check the unit and the booking before setting urgency (e.g. a guest arriving today makes it more urgent) | eval cases that need the booking to get urgency right | 6 |

## Limits
- Python 3.12, FastAPI, Pydantic, Anthropic Python SDK
- Synthetic data only
- The API key comes from the environment, never from the repo
- MIT licence

## Out of scope
- Replying to guests
- A user interface
- Real customer data

The detailed guarantees and their reasons are in [02-design.md](02-design.md).
