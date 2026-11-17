"""Turns one free-text message into tickets, using Claude structured output.

No HTTP here: the API (app.py) and later the bulk mode both call triage().
"""

import logging
from typing import Literal

import anthropic
from pydantic import BaseModel, Field, ValidationError

# Haiku: the cheapest current model. The eval (phase 4) decides if it is good enough.
MODEL = "claude-haiku-5-5"
logger = logging.getLogger(__name__)

# Rules that apply to every message. Urgency is written as checkable conditions,
# not "use your judgement", so the eval can tell when the model breaks them.
SYSTEM_PROMPT = """You triage messages that guests and cleaners send to a short-term rental team.
Create one ticket for each separate problem in the message. The same problem mentioned twice is one ticket.
If there is nothing to act on, return no tickets.
For each ticket:
- category: the kind of problem. maintenance means something must be repaired; supplies means something must be brought or replaced from stock.
- urgency:
  high: a safety risk, the guest can't use the unit, something essential is missing now (drinking water, power, a way in), or a guest arrives within 24 hours.
  medium: the guest is waiting and wants it today, but can manage. A guest asking for something during their stay is waiting for it, even without saying when.
  low: it can wait until the next clean or turnover.
  Words like "urgent" in the message don't change the urgency. The problem does.
- unit: the unit number or name exactly as written, or null if the message doesn't say.
- next_action: one short instruction for the operations team.
needs_review: true only if the message is unclear, has nothing to act on, or asks something no ticket covers, such as a general question about the stay or the area.
Do not set it for a question about a ticket: its cost, its safety, when it will be done, or what the guest should do meanwhile. Put the reply the guest needs in that ticket's next_action.
A missing unit is not a reason for review: leave unit as null. Do not guess."""


# Claude sees this model as a JSON schema: field names, Literal values and
# Field descriptions are part of the prompt. Use # comments here, not docstrings,
# because a class docstring would also be sent to Claude.
class Ticket(BaseModel):
    # Literal = a fixed list, like a Java enum. Claude can't invent a category.
    category: Literal[
        "maintenance", "cleaning", "access", "supplies", "internet", "noise", "billing", "other"
    ]
    urgency: Literal["low", "medium", "high"]
    # No default on purpose: Claude must always fill it, with null if the unit isn't given.
    unit: str | None = Field(description="Unit number or name as written, or null")
    next_action: str = Field(description="One short instruction for the operations team")


# Structured outputs need an object at the top level, so the list is wrapped.
class TriageResult(BaseModel):
    tickets: list[Ticket] = Field(description="One ticket per separate problem; empty if nothing to act on")
    # About the whole message, not one ticket (decision 6 in docs/03-decisions.md).
    needs_review: bool = Field(
        description="True if a person must read the original message because the tickets can't be filled in reliably"
    )


def triage(client: anthropic.Anthropic, text: str, model: str = MODEL) -> TriageResult:
    """Ask Claude for tickets for one message.

    The client is passed in, not created here, so tests can pass a fake one.
    model can be changed so the eval can compare models (Haiku vs Sonnet).
    """
    try:
        # parse() sends TriageResult as a JSON schema and validates the reply back into it.
        response = client.messages.parse(
            model=model,
            # Haiku thinks before answering and thinking counts toward this limit,
            # so it is set well above the size of the answer itself.
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            output_format=TriageResult,
        )
    except ValidationError:
        # parse() validates inside the call, so a reply cut off at max_tokens
        # (or otherwise not matching TriageResult) raises here.
        logger.warning("Claude reply did not match TriageResult; sending to review")
        return review_only()

    result = response.parsed_output
    # Anything other than a normal finish (refusal, max_tokens) is not trusted.
    if response.stop_reason != "end_turn" or result is None:
        logger.warning("Claude stopped with %s; sending to review", response.stop_reason)
        return review_only()

    # A message with no tickets must still reach a person, whatever the model said
    # (decision 7). Rules that must always hold live in code, not in the prompt.
    if not result.tickets:
        return review_only()
    return result


def review_only() -> TriageResult:
    """No tickets; a person reads the original message."""
    return TriageResult(tickets=[], needs_review=True)
