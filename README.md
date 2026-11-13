# guest-message-triage

A small service that reads free-text messages from guests and cleaners and turns them into a structured maintenance ticket, using the Claude API.

For example, "the AC in unit 4 is leaking, guest checks in at 3pm" should become a ticket with a category, an urgency, the unit, and what to do next.

## Status

Work in progress. Today it has the FastAPI skeleton: a health check and a `POST /messages` endpoint that validates the input. The Claude call is the next step. Progress is in [docs/00-status.md](docs/00-status.md).

## Run it

You need [uv](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env        # then put your Anthropic API key in .env
uv run --env-file .env uvicorn guest_message_triage.app:app --reload
```

API docs: http://127.0.0.1:8000/docs

Tests: `uv run pytest`

## Plan

- Claude structured output: the reply must match a Pydantic model
- Unclear messages go to "needs a human" instead of a guess
- Save tickets in Postgres
- An eval set of labelled synthetic messages, with accuracy per field
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
