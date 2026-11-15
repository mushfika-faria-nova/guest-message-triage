"""HTTP layer: receives messages and returns tickets. The triage logic lives in triage.py."""

import logging
from functools import lru_cache
from typing import Annotated

import anthropic
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from guest_message_triage.db import get_session, save_triage
from guest_message_triage.triage import TriageResult, review_only, triage

app = FastAPI(title="guest-message-triage")

logger = logging.getLogger(__name__)


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
    # The default timeout is 10 minutes, far too long for an API call.
    # Worst case is about 3 x 30s: the first try plus 2 SDK retries.
    return anthropic.Anthropic(timeout=30.0, max_retries=2)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Plain def, not async def: the Anthropic client used here is synchronous,
# and FastAPI runs plain def endpoints in a thread pool so they don't block.
@app.post("/messages")
def create_message(
    msg: MessageIn,
    client: Annotated[anthropic.Anthropic, Depends(get_client)],
    session: Annotated[Session, Depends(get_session)],
) -> TriageResult:
    try:
        result = triage(client, msg.text)
    except anthropic.EnforcedSpendLimitReachedError:
        # A subclass of RateLimitError, but it doesn't clear by itself. Checked first.
        logger.error("Claude spend limit reached; saving message for review")
        result = review_only()
    except (anthropic.APIConnectionError, anthropic.InternalServerError, anthropic.RateLimitError):
        # Temporary, and the SDK has already retried twice. Keep the message for a person.
        logger.warning("Claude unavailable; saving message for review", exc_info=True)
        result = review_only()
    except anthropic.APIError:
        # Not temporary (bad key, bad request): someone must fix it. The message is still kept.
        logger.exception("Claude call failed; saving message for review")
        result = review_only()
    save_triage(session, msg.text, msg.sender, result)
    return result

