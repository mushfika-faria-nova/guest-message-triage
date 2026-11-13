"""HTTP layer: receives messages and returns tickets. The triage logic lives in triage.py."""

from functools import lru_cache
from typing import Annotated

import anthropic
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from guest_message_triage.triage import TriageResult, triage

app = FastAPI(title="guest-message-triage")


# Request body. FastAPI validates it before the endpoint runs, so invalid input
# returns 422 and never reaches Claude (no cost).
class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    sender: str | None = None


# lru_cache makes this a singleton: one client for the whole app, so HTTP
# connections are reused. The client reads ANTHROPIC_API_KEY from the environment.
# Tests swap it for a fake with app.dependency_overrides.
@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Plain def, not async def: the Anthropic client used here is synchronous,
# and FastAPI runs plain def endpoints in a thread pool so they don't block.
@app.post("/messages")
def create_message(
    msg: MessageIn,
    client: Annotated[anthropic.Anthropic, Depends(get_client)],
) -> TriageResult:
    return triage(client, msg.text)
