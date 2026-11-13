from types import SimpleNamespace


class FakeMessages:
    """Stands in for client.messages; records every call instead of calling Claude."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(parsed_output=self.result)


class FakeClient:
    def __init__(self, result):
        self.messages = FakeMessages(result)
