"""Cross-file checks for the rule, lookup, and change envelopes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from navigator.changes import build_changes
from navigator.corpus import SourceDocument
from navigator.errors import CommandError
from navigator.method_note import write_method_note
from navigator.validate import run_validate, submission_problems

SPAN = "Santa Ana limits residential rent increases to no more than 3 percent per year under the ordinance."


def document() -> SourceDocument:
    return SourceDocument(
        doc_id="F100",
        jurisdictions="CA",
        url="https://example.test/f100",
        source_type="official",
        retrieved_at="2026-10-01T00:00Z",
        text_file="text/F100.txt",
        text=SPAN,
    )


def rule(rule_id: str, status: str, jurisdiction: str = "CA", level: str = "state") -> dict:
    return {
        "team_rule_id": rule_id,
        "jurisdiction": jurisdiction,
        "level": level,
        "category": "rent_increase_limits" if jurisdiction.startswith("Santa Ana") else "algorithmic_rent_setting",
        "status": status,
        "title": "Fixture rule",
        "requirement": "The fixture states the requirement in plain language.",
        "citation": "Fixture citation",
        "source_url": "https://example.test/f100",
        "source_doc_id": "F100",
        "quoted_span": SPAN,
    }


def rules() -> list[dict]:
    return [
        rule("r-0001", "in_force", "Santa Ana, CA", "city"),
        rule("MA-RENT-P1", "failed"),
        rule("MA-ALG-P1", "pending"),
        rule("MA-ALG-P2", "pending"),
    ]


def geocodes() -> dict[str, dict]:
    return {
        "A0001": {
            "address_id": "A0001",
            "legal_state": "CA",
            "legal_city": "Los Angeles",
        }
    }


def passing_submission() -> tuple[list[dict], dict, dict, dict]:
    places = geocodes()
    return (
        rules(),
        {"as_of": "2026-10-01", "lookups": {"A0001": []}},
        build_changes(places),
        places,
    )


def test_fixture_envelopes_pass():
    catalog, lookups, changes, places = passing_submission()
    assert submission_problems(catalog, lookups, changes, places, [document()], ["A0001"]) == []


def test_span_must_be_the_file_slice():
    catalog, lookups, changes, places = passing_submission()
    catalog[0]["quoted_span"] = "This sentence is not in the captured document at all."
    problems = submission_problems(catalog, lookups, changes, places, [document()], ["A0001"])
    assert any("exact slice" in problem for problem in problems)


def test_lookups_need_every_sample_id_and_exclude_santa_ana():
    catalog, lookups, changes, places = passing_submission()
    lookups["lookups"] = {
        "A0001": [
            {
                "team_rule_id": "r-0001",
                "result": "applies",
                "explanation": "Santa Ana was attached to a sample address.",
                "conflict_flag": False,
            }
        ]
    }
    problems = submission_problems(catalog, lookups, changes, places, [document()], ["A0001", "A0002"])
    assert any("missing" in problem for problem in problems)
    assert any("Santa Ana" in problem for problem in problems)


def test_failed_rent_question_never_applies():
    catalog, lookups, changes, places = passing_submission()
    lookups["lookups"] = {
        "A0001": [
            {
                "team_rule_id": "MA-RENT-P1",
                "result": "applies",
                "explanation": "A rent cap was reported.",
                "conflict_flag": False,
            }
        ]
    }
    problems = submission_problems(catalog, lookups, changes, places, [document()], ["A0001"])
    assert any("MA-RENT-P1 must not apply" in problem for problem in problems)


def test_change_notes_name_the_required_facts():
    catalog, lookups, changes, places = passing_submission()
    changes["T5"]["notes"] = "No note about the outcome."
    changes["T2"]["affected_address_ids"] = ["A9999"]
    problems = submission_problems(catalog, lookups, changes, places, [document()], ["A0001"])
    assert any("T5" in problem for problem in problems)
    assert any("T2" in problem for problem in problems)


def test_method_note_describes_spans_and_unknowns(tmp_path: Path):
    path = write_method_note(tmp_path / "method-note.md")
    text = path.read_text(encoding="utf-8").casefold()
    assert "link-only" in text
    assert "d056" in text
    assert "exact slice" in text
    assert "unknown" in text
    assert "certificate of occupancy" in text
    assert "unit count" in text
    assert "owner" in text


def test_validate_refuses_a_missing_catalog(tmp_path: Path):
    with pytest.raises(CommandError, match="Rules file not found"):
        run_validate(["--rules", str(tmp_path / "rules.json")])


def test_rules_envelope_is_a_rules_list(tmp_path: Path):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"rules": rules()}), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload["rules"], list)
    assert payload["rules"][0]["quoted_span"] == SPAN
