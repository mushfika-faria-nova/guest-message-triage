from fakes import FakeClient, cut_off_reply

from guest_message_triage.triage import Ticket, TriageResult, triage

REVIEW = TriageResult(tickets=[], needs_review=True)

TOWELS = Ticket(category="supplies", urgency="medium", unit="12B", next_action="Bring towels to 12B.")


def test_no_tickets_always_goes_to_review():
    # The model said "no tickets, no review" (seen live for "hi"); the code must override it.
    client = FakeClient(TriageResult(tickets=[], needs_review=False))
    assert triage(client, "hi").needs_review is True


def test_tickets_keep_the_models_review_flag():
    client = FakeClient(TriageResult(tickets=[TOWELS], needs_review=False))
    assert triage(client, "towels missing in 12B").needs_review is False


def test_cut_off_reply_goes_to_review():
    client = FakeClient(error=cut_off_reply())
    assert triage(client, "AC leaking in 4") == REVIEW


def test_refusal_goes_to_review_even_with_tickets():
    # After a refusal nothing in the reply is trusted, not even parsed tickets.
    client = FakeClient(TriageResult(tickets=[TOWELS], needs_review=False), stop_reason="refusal")
    assert triage(client, "towels missing in 12B") == REVIEW
