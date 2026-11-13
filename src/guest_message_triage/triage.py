"""Turns one free-text message into tickets, using Claude structured output.

No HTTP here: the API (app.py) and later the bulk mode both call triage().
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

# Haiku: the cheapest current model. The eval (phase 4) decides if it is good enough.
MODEL = "claude-haiku-5-5"

# Rules that apply to every message. Urgency is written as checkable conditions,
# not "use your judgement", so the eval can tell when the model breaks them.
SYSTEM_PROMPT = """You triage messages that guests and cleaners send to a short-term rental team.
Create one ticket for each separate problem in the message. The same problem mentioned twice is one ticket.
If there is nothing to act on, return no tickets.
For each ticket:
- category: the kind of problem.
- urgency: high if it is a safety risk, stops a guest from using the unit, or a guest arrives within 24 hours; medium if it needs fixing within a few days; low otherwise.
- unit: the unit number or name exactly as written, or null if the message doesn't say.
- next_action: one short instruction for the operations team.
needs_review: true if a person should read the original message, because it is unclear or you are not sure about a ticket. Do not guess."""


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


def triage(client: anthropic.Anthropic, text: str) -> TriageResult:
    """Ask Claude for tickets for one message.

    The client is passed in, not created here, so tests can pass a fake one.
    """
    # parse() sends TriageResult as a JSON schema and validates the reply back into it.
    response = client.messages.parse(
        model=MODEL,
        # Haiku thinks before answering and thinking counts toward this limit,
        # so it is set well above the size of the answer itself.
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        output_format=TriageResult,
    )
    result = response.parsed_output
    # A message with no tickets must still reach a person, whatever the model said
    # (decision 7). Rules that must always hold live in code, not in the prompt.
    if not result.tickets:
        result.needs_review = True
    return result
