"""Change-case tests. Fixture geocodes stand in for the Census cache."""

from __future__ import annotations

import json
from pathlib import Path

from navigator.changes import build_changes
from navigator.coverage import evaluate_address
from navigator.models import JurisdictionStack, RuleRecord, SampleAddress

AS_OF = "2026-10-01"


def address(address_id: str, state: str, postal_city: str) -> SampleAddress:
    return SampleAddress(
        address_id=address_id,
        street_address="1 Main St",
        postal_city=postal_city,
        state=state,
        zip="00000",
        year_built=1990,
        units=10,
        use_code="",
        use_description="",
        source_dataset="fixture",
        retrieved_at="2026-10-01T00:00Z",
    )


def stack(address_id: str, state: str, city: str, postal_city: str) -> dict:
    return {
        "address_id": address_id,
        "match_status": "matched",
        "legal_state": state,
        "legal_county": city,
        "legal_city": city,
        "postal_city": postal_city,
        "retrieved_at": "2026-10-01T00:00Z",
    }


def geocodes() -> dict[str, dict]:
    return {
        "A0100": stack("A0100", "CA", "Los Angeles", "Van Nuys"),
        "A0200": stack("A0200", "NJ", "Hoboken", "Hoboken"),
        "A0201": stack("A0201", "NJ", "Jersey City", "Jersey City"),
        "A0202": stack("A0202", "NJ", "Newark", "Newark"),
        "A0300": stack("A0300", "MA", "Boston", "Dorchester"),
        "A0301": stack("A0301", "MA", "Cambridge", "Cambridge"),
    }


def rule(**overrides) -> RuleRecord:
    record = RuleRecord(
        team_rule_id="CA-ALG-01",
        jurisdiction="CA",
        level="state",
        category="algorithmic_rent_setting",
        status="in_force",
        title="California algorithmic pricing ban",
        requirement="Use of algorithmic rent-setting software is prohibited.",
        citation="AB 325",
        source_url="https://example.test/ca",
        quoted_span="Use of algorithmic rent-setting software is prohibited.",
        effective_date="2026-01-01",
        source_doc_id="F200",
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


def test_change_sets_follow_legal_city_and_state():
    report = build_changes(geocodes())
    assert report["T1"]["affected_address_ids"] == ["A0100"]
    assert "conflict_flag_address_ids" not in report["T1"]
    assert report["T2"]["affected_address_ids"] == ["A0200", "A0201"]
    assert "A0202" not in report["T2"]["affected_address_ids"]
    assert "Hoboken" in report["T2"]["notes"]
    assert "Jersey City" in report["T2"]["notes"]
    assert "Newark" in report["T2"]["notes"]
    assert report["T3"]["affected_address_ids"] == ["A0200", "A0201", "A0202"]
    assert report["T3"]["conflict_flag_address_ids"] == ["A0200", "A0201"]
    assert report["T4"]["affected_address_ids"] == ["A0300", "A0301"]
    assert "pending" in report["T4"]["notes"].lower()
    assert "enacted" in report["T4"]["notes"].lower()
    assert report["T5"]["affected_address_ids"] == []
    assert "failed" in report["T5"]["notes"].lower()
    assert "Boston" in report["T5"]["notes"]
    assert "Cambridge" in report["T5"]["notes"]


def test_california_rule_flips_on_the_effective_date():
    place = address("A0100", "CA", "Van Nuys")
    legal = JurisdictionStack("A0100", "matched", "CA", "Los Angeles", "Los Angeles", "Van Nuys", "2026-10-01T00:00Z")
    before = evaluate_address(place, legal, [rule()], "2025-12-31")
    after = evaluate_address(place, legal, [rule()], "2026-01-02")
    assert before[0].result == "not_yet_effective"
    assert after[0].result == "applies"


def test_local_bans_stay_inside_their_cities():
    hoboken = address("A0200", "NJ", "Hoboken")
    newark = address("A0202", "NJ", "Newark")
    hoboken_stack = JurisdictionStack("A0200", "matched", "NJ", "Hudson", "Hoboken", "Hoboken", "2026-10-01T00:00Z")
    newark_stack = JurisdictionStack("A0202", "matched", "NJ", "Essex", "Newark", "Newark", "2026-10-01T00:00Z")
    bans = [
        rule(team_rule_id="HOB-ALG-01", jurisdiction="Hoboken, NJ", level="city", effective_date=None),
        rule(team_rule_id="JC-ALG-01", jurisdiction="Jersey City, NJ", level="city", effective_date=None),
    ]
    hoboken_ids = [row.team_rule_id for row in evaluate_address(hoboken, hoboken_stack, bans, AS_OF)]
    newark_ids = [row.team_rule_id for row in evaluate_address(newark, newark_stack, bans, AS_OF)]
    assert hoboken_ids == ["HOB-ALG-01"]
    assert newark_ids == []


def test_changes_command_writes_sorted_ids(tmp_path: Path):
    from navigator.__main__ import main

    cache = tmp_path / "geocodes.json"
    output = tmp_path / "changes.json"
    cache.write_text(json.dumps({"geocodes": geocodes()}), encoding="utf-8")
    code = main(["changes", "--geocodes", str(cache), "--output", str(output)])
    assert code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert list(report) == ["T1", "T2", "T3", "T4", "T5"]
    assert report["T5"]["affected_address_ids"] == []


def test_demo_page_lists_change_cases():
    html = Path("src/navigator/demo/index.html").read_text(encoding="utf-8")
    assert 'id="changes"' in html
    assert "output/changes.json" in html
