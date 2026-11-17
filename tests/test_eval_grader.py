"""The eval's grader must give full marks to the right answer and fail wrong ones,
or the eval's numbers mean nothing. No API calls here."""

import json
import sys
from pathlib import Path

EVALS = Path(__file__).parent.parent / "evals"
sys.path.insert(0, str(EVALS))

from run import grade, norm_unit  # noqa: E402

CASES = [json.loads(line) for line in (EVALS / "cases.jsonl").read_text().splitlines()]


def test_expected_answer_scores_full_marks_on_every_case():
    for case in CASES:
        scores = grade(case["expected"], case["expected"])
        assert all(v == 1 for v in scores.values()), (case["id"], scores)


def test_empty_answer_fails_every_ticket_case():
    empty = {"tickets": [], "needs_review": False}
    for case in CASES:
        if not case["expected"]["needs_review"]:
            assert grade(case["expected"], empty)["category"] == 0, case["id"]


def test_wrong_review_flag_fails():
    for case in CASES:
        wrong = {**case["expected"], "needs_review": not case["expected"]["needs_review"]}
        assert grade(case["expected"], wrong)["needs_review"] == 0, case["id"]


def test_ticket_order_does_not_matter():
    expected = {"needs_review": False, "tickets": [
        {"category": "maintenance", "urgency": "high", "unit": "7A"},
        {"category": "supplies", "urgency": "low", "unit": "7A"},
    ]}
    swapped = {**expected, "tickets": list(reversed(expected["tickets"]))}
    assert all(v == 1 for v in grade(expected, swapped).values())


def test_unit_words_are_ignored():
    assert norm_unit("Room 201") == norm_unit("roo 201") == norm_unit("201") == "201"
    assert norm_unit("Lake House") == "lake house"
