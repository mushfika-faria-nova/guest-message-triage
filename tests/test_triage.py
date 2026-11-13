from fakes import FakeClient

from guest_message_triage.triage import Ticket, TriageResult, triage

TOWELS = Ticket(category="supplies", urgency="medium", unit="12B", next_action="Bring towels to 12B.")


def test_no_tickets_always_goes_to_review():
    # The model said "no tickets, no review" (seen live for "hi"); the code must override it.
    client = FakeClient(TriageResult(tickets=[], needs_review=False))
    assert triage(client, "hi").needs_review is True


def test_tickets_keep_the_models_review_flag():
    client = FakeClient(TriageResult(tickets=[TOWELS], needs_review=False))
    assert triage(client, "towels missing in 12B").needs_review is False
