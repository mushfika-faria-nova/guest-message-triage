# guest-message-triage

A small service that reads free-text messages from guests and cleaners and turns them into a structured maintenance ticket, using the Claude API.

For example, "the AC in unit 4 is leaking, guest checks in at 3pm" should become a ticket with a category, an urgency, the unit, and what to do next.

## Status

Work in progress. Today `POST /messages` sends the message to Claude, gets back one ticket per problem, and saves the message and its tickets in Postgres. Progress is in [docs/00-status.md](docs/00-status.md).

## Run it

You need [uv](https://docs.astral.sh/uv/) and Docker.

```sh
uv sync
cp .env.example .env        # then put your Anthropic API key in .env
docker compose up -d        # Postgres 18 on 127.0.0.1:5432
uv run --env-file .env alembic upgrade head
uv run --env-file .env uvicorn guest_message_triage.app:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Try it

With the server running, in a second terminal from the repo folder. Each message is one Claude call (a fraction of a cent on Haiku).

```sh
# Two problems in one message: two tickets
curl -s -X POST localhost:8000/messages -H 'Content-Type: application/json' -d '{"text": "No towels in 12B and the wifi is down", "sender": "guest"}'

# Nothing to act on: no tickets, needs_review true
curl -s -X POST localhost:8000/messages -H 'Content-Type: application/json' -d '{"text": "thanks!", "sender": "guest"}'

# Invalid input: 422, Claude is not called, nothing is saved
curl -s -i -X POST localhost:8000/messages -H 'Content-Type: application/json' -d '{"text": ""}'
```

See what was saved:

```sh
docker compose exec db psql -U triage -c "select id, sender, needs_review, text from messages order by id"
docker compose exec db psql -U triage -c "select m.id as msg, m.needs_review, t.category, t.urgency, t.unit, t.next_action from messages m left join tickets t on t.message_id = m.id order by m.id, t.id"
```

`docker compose exec db psql -U triage` opens a SQL prompt (`\dt` lists tables, `\q` quits). `docker compose down -v` deletes the database; run `alembic upgrade head` again after it.

## Database changes

Tables are defined in `src/guest_message_triage/db.py` and created by Alembic migrations in `migrations/versions/`.

```sh
uv run --env-file .env alembic revision --autogenerate -m "what changed"   # after changing db.py; read the new file before applying
uv run --env-file .env alembic upgrade head                                # apply
uv run --env-file .env alembic check                                       # models and database match?
```

## Tests

Tests use a separate database and a fake Claude client, so they cost nothing:

```sh
docker compose exec db createdb -U triage triage_test   # once
uv run pytest
```

## Evaluation

40 synthetic guest and cleaner messages, each labelled with the tickets I expect (`evals/cases.md`, with the labelling rules at the top). Each message goes through the real `triage()` twice on Claude Haiku, and code grades every field against the label.

| field | baseline prompt | v1 | v2 (current) |
|---|---|---|---|
| needs_review (40 cases) | 95.0% | 91.2% | 98.8% |
| category (31 ticket cases) | 91.9% | 96.8% | 96.8% |
| urgency (31) | 71.0% | 84.7% | 86.3% |
| unit (31) | 100% | 100% | 100% |

- v1 wrote my urgency, category and review rules into the prompt. v2 changed only the review rule's wording.
- Baseline to v2, urgency: +15.3 points, 95% range +3.2 to +27.5 (paired over the same cases), so the gain is not noise.
- Cost: about $0.02 for 80 calls on Haiku (about 1,150 input and 70–590 output tokens per message).
- The prompt was tuned on these 40 cases, so 86% is optimistic. A check on new cases is next.

Run it:

```sh
uv run --env-file .env python evals/run.py --approve-harness --variant v3   # a new prompt version
uv run --env-file .env python evals/run.py --regrade --variant v2           # re-grade saved answers, no API calls
```

The runner stops if the cases, grader or prompt changed since the last approval, so scores from different setups never get mixed.

## Plan

- Claude structured output: the reply must match a Pydantic model (done)
- One ticket per problem; unclear messages are marked for a person to review instead of a guess (done)
- Save messages and tickets in Postgres (done)
- Failure handling: Claude errors, cut-off or invalid replies (done)
- An eval set of labelled synthetic messages, with accuracy per field (done, see Evaluation above)
- Cost per message, comparing models
- Bulk mode: hundreds of messages in one run, through the Message Batches API
- One agent step: Claude looks up the unit and the booking before setting urgency

All data in this repo is synthetic.

## Docs

- [Requirements](docs/01-requirements.md)
- [Design](docs/02-design.md)
- [Decisions](docs/03-decisions.md)

## License

MIT
