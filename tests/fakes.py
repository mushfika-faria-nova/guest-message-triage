from types import SimpleNamespace

import anthropic
import httpx2
from pydantic import ValidationError

from guest_message_triage.triage import TriageResult


class FakeMessages:
    """Stands in for client.messages; records every call instead of calling Claude."""

    def __init__(self, result, stop_reason, error):
        self.result = result
        self.stop_reason = stop_reason
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(parsed_output=self.result, stop_reason=self.stop_reason)


class FakeClient:
    def __init__(self, result=None, stop_reason="end_turn", error=None):
        self.messages = FakeMessages(result, stop_reason, error)


def cut_off_reply():
    """The ValidationError parse() raises when Claude's JSON is cut off."""
    try:
        TriageResult.model_validate_json('{"tickets": [')
    except ValidationError as e:
        return e


REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def api_error(cls, status):
    """An SDK error for an HTTP status, e.g. api_error(anthropic.InternalServerError, 500)."""
    return cls("fake", response=httpx2.Response(status, request=REQUEST), body=None)


def connection_error():
    return anthropic.APIConnectionError(request=REQUEST)
