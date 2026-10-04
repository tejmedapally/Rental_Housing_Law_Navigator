"""Verifier tests for the cited rule catalog. These call the fixture corpus only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from navigator.corpus import load_corpus_directory
from navigator.extract import verify_candidates, write_rules
from navigator.validate import catalog_problems

FIXTURE = Path(__file__).parent / "fixtures" / "corpus"
SPAN = "A security deposit may not exceed one month of rent. Effective 2026-01-01."


def documents() -> dict:
    return {item.doc_id: item for item in load_corpus_directory(FIXTURE)}


def candidate(**overrides) -> dict:
    record = {
        "team_rule_id": "r-0001",
        "jurisdiction": "CA",
        "level": "state",
        "category": "security_deposits",
        "status": "in_force",
        "title": "Deposit cap",
        "requirement": "A security deposit may not exceed one month of rent.",
        "citation": "Fixture § 1",
        "source_doc_id": "F001",
        "source_url": "https://example.test/f001",
        "quoted_span": SPAN,
        "effective_date": "2026-01-01",
    }
    record.update(overrides)
    return record


def test_collapsed_span_is_stored_as_the_file_slice():
    accepted, rejected = verify_candidates([candidate()], documents())
    assert rejected == []
    assert len(accepted) == 1
    stored = accepted[0].quoted_span
    assert stored in (FIXTURE / "text" / "F001.txt").read_text(encoding="utf-8")
    assert "\n" in stored
    assert stored.replace("\n", " ") == SPAN


def test_span_missing_from_the_source_is_rejected():
    accepted, rejected = verify_candidates(
        [candidate(quoted_span="This sentence does not appear in the fixture text.")],
        documents(),
    )
    assert accepted == []
    assert rejected


def test_short_span_is_rejected():
    accepted, rejected = verify_candidates(
        [candidate(quoted_span="A security deposit", effective_date=None)],
        documents(),
    )
    assert accepted == []
    assert rejected


def test_link_only_document_is_rejected():
    accepted, rejected = verify_candidates(
        [candidate(source_doc_id="F002", source_url="https://example.test/f002")],
        documents(),
    )
    assert accepted == []
    assert any("F002" in item for item in rejected)


def test_effective_date_missing_from_the_span_is_rejected():
    accepted, rejected = verify_candidates(
        [candidate(effective_date="1999-01-01")],
        documents(),
    )
    assert accepted == []
    assert rejected


def test_duplicate_team_rule_id_keeps_the_first_record():
    accepted, rejected = verify_candidates([candidate(), candidate()], documents())
    assert len(accepted) == 1
    assert rejected


def test_invalid_status_is_rejected():
    accepted, rejected = verify_candidates([candidate(status="maybe")], documents())
    assert accepted == []
    assert rejected


def test_string_coverage_conditions_are_rejected():
    accepted, rejected = verify_candidates(
        [candidate(coverage_conditions="Residential rentals statewide")],
        documents(),
    )
    assert accepted == []
    assert rejected


def test_missing_id_is_assigned_r_number(tmp_path: Path):
    raw = candidate()
    del raw["team_rule_id"]
    accepted, rejected = verify_candidates([raw], documents())
    assert rejected == []
    assert accepted[0].team_rule_id == "r-0001"
    path = tmp_path / "rules.json"
    write_rules(accepted, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["rules"][0]["team_rule_id"] == "r-0001"
    assert payload["rules"][0]["quoted_span"] == accepted[0].quoted_span


def test_catalog_problems_cover_schema_santa_ana_and_status():
    valid = [
        candidate(
            team_rule_id="r-0100",
            jurisdiction="Santa Ana, CA",
            level="city",
            quoted_span=SPAN,
        ),
        candidate(team_rule_id="MA-RENT-P1", status="failed", effective_date=None),
        candidate(team_rule_id="MA-ALG-P1", status="pending", effective_date=None),
        candidate(team_rule_id="MA-ALG-P2", status="pending", effective_date=None),
    ]
    accepted, rejected = verify_candidates(valid, documents())
    assert rejected == []
    assert catalog_problems([_as_dict(item) for item in accepted], link_only_ids={"F002"}) == []

    broken = [_as_dict(item) for item in accepted]
    broken[1]["status"] = "in_force"
    broken.append(dict(broken[0], team_rule_id="r-0101", source_doc_id="F002"))
    problems = catalog_problems(broken, link_only_ids={"F002"})
    assert any("Santa Ana" in item or "MA-RENT-P1" in item or "F002" in item for item in problems)


def _as_dict(rule) -> dict:
    from navigator.extract import rule_to_dict

    return rule_to_dict(rule)


def test_extract_command_omits_rejected_candidates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from navigator.__main__ import main

    def forbid_network(*_args, **_kwargs):
        raise AssertionError("extract must not fetch a link-only document")

    monkeypatch.setattr("urllib.request.urlopen", forbid_network)
    candidates = tmp_path / "candidates.json"
    output = tmp_path / "rules.json"
    output.write_text('{"rules":[{"keep":true}]}', encoding="utf-8")
    candidates.write_text(
        json.dumps({"rules": [candidate(), candidate(source_doc_id="F002", source_url="https://example.test/f002", team_rule_id="r-0002")]}),
        encoding="utf-8",
    )
    code = main(
        [
            "extract",
            "--candidates",
            str(candidates),
            "--corpus",
            str(FIXTURE),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [item["team_rule_id"] for item in payload["rules"]] == ["r-0001"]


def test_rejected_extract_keeps_the_existing_catalog(tmp_path: Path):
    from navigator.__main__ import main

    output = tmp_path / "rules.json"
    output.write_text(json.dumps({"rules": [{"team_rule_id": "r-0009"}]}), encoding="utf-8")
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps({"rules": [candidate(quoted_span="this sentence is not in the captured file")]}),
        encoding="utf-8",
    )
    code = main(["extract", "--candidates", str(candidates), "--corpus", str(FIXTURE), "--output", str(output)])
    assert code == 1
    assert json.loads(output.read_text(encoding="utf-8"))["rules"][0]["team_rule_id"] == "r-0009"


def test_reserved_bill_id_replaces_the_generated_id():
    from navigator.extract import apply_reserved_ids
    from navigator.models import RuleRecord

    rule = RuleRecord(
        team_rule_id="r-0112",
        jurisdiction="MA",
        level="state",
        category="algorithmic_rent_setting",
        status="pending",
        title="H.5222",
        requirement="Pending algorithmic rent bill.",
        citation="H.5222",
        source_url="https://example.test/h5222",
        quoted_span="x" * 20,
        source_doc_id="D045",
    )
    apply_reserved_ids([rule])
    assert rule.team_rule_id == "MA-ALG-P2"


def test_bind_source_fills_the_document_that_was_sent():
    from navigator.corpus import SourceDocument
    from navigator.extract import bind_source

    document = SourceDocument("D001", "CA", "https://example.test/d001", "official", "2026-10-01", "text/D001.txt", "x" * 40)
    bound = bind_source([{"quoted_span": "x" * 20, "source_doc_id": "", "source_url": "https://wrong.example"}], document)
    assert bound[0]["source_doc_id"] == "D001"
    assert bound[0]["source_url"] == "https://example.test/d001"


def test_anthropic_key_is_a_request_header(monkeypatch: pytest.MonkeyPatch):
    from navigator.corpus import SourceDocument
    from navigator.extract import propose_rules

    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"content": [{"type": "text", "text": '{"rules": []}'}]}).encode()

    def fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        return Response()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("NAVIGATOR_MODEL_BASE_URL", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    document = SourceDocument("D900", "CA", "https://example.test/d900", "official", "2026-10-01", "text/D900.txt", "A" * 40)
    assert propose_rules(document) == []
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert "test-key" not in str(captured["url"])
