"""Lookup tests. They use a saved Census match and do not call the network."""

from __future__ import annotations

import json
from pathlib import Path

from navigator.coverage import build_lookups, evaluate_address
from navigator.geocode import parse_census_match
from navigator.models import CoverageConditions, Geography, RuleRecord, SampleAddress

FIXTURE = Path(__file__).parent / "fixtures" / "census_match.json"
AS_OF = "2026-10-01"


def van_nuys() -> SampleAddress:
    return SampleAddress(
        address_id="A9001",
        street_address="14547 SYLVAN ST",
        postal_city="Van Nuys",
        state="CA",
        zip="91401",
        year_built=1970,
        units=20,
        use_code="0500",
        use_description="Five or more apartments",
        source_dataset="fixture",
        retrieved_at="2026-10-01T00:00Z",
    )


def rule(**overrides) -> RuleRecord:
    record = RuleRecord(
        team_rule_id="r-0001",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="Local rent cap",
        requirement="Annual rent increases are limited for covered units.",
        citation="Fixture rent law",
        source_url="https://example.test/la",
        quoted_span="Annual rent increases are limited for covered units.",
        source_doc_id="F100",
        coverage_conditions=CoverageConditions(
            summary="Los Angeles rental units",
            geography=Geography("city", "Los Angeles, CA"),
        ),
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


def stack_for(address: SampleAddress):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return parse_census_match(address, payload, retrieved_at="2026-10-01T00:00Z")


def test_neighborhood_mailing_city_resolves_to_incorporated_place():
    address = van_nuys()
    stack = stack_for(address)
    assert stack.legal_city == "Los Angeles"
    assert stack.legal_state == "CA"
    assert stack.postal_city == "Van Nuys"
    assert stack.legal_city != address.postal_city


def test_jersey_city_basename_is_not_shortened():
    address = van_nuys()
    payload = {
        "result": {
            "addressMatches": [
                {
                    "geographies": {
                        "States": [{"STUSAB": "NJ"}],
                        "Counties": [{"BASENAME": "Hudson", "NAME": "Hudson County"}],
                        "Incorporated Places": [{"BASENAME": "Jersey City", "NAME": "Jersey City city"}],
                    }
                }
            ]
        }
    }
    stack = parse_census_match(address, payload, retrieved_at="2026-10-01T00:00Z")
    assert stack.legal_city == "Jersey City"
    assert stack.legal_county == "Hudson"


def test_city_rule_uses_legal_city_not_postal_city():
    address = van_nuys()
    stack = stack_for(address)
    rows = evaluate_address(address, stack, [rule()], AS_OF)
    assert [row.team_rule_id for row in rows] == ["r-0001"]
    assert rows[0].result == "applies"
    other = rule(team_rule_id="r-0002", jurisdiction="Van Nuys, CA")
    assert evaluate_address(address, stack, [other], AS_OF) == []


def test_santa_ana_rule_is_omitted_for_every_sample_address():
    address = van_nuys()
    stack = stack_for(address)
    santa_ana = rule(team_rule_id="r-0100", jurisdiction="Santa Ana, CA")
    assert evaluate_address(address, stack, [santa_ana], AS_OF) == []
    unresolved = stack_for(address)
    unresolved.match_status = "unmatched"
    unresolved.legal_city = None
    assert evaluate_address(address, unresolved, [santa_ana], AS_OF) == []


def test_missing_unit_count_is_unknown():
    address = van_nuys()
    address.units = None
    covered = rule(
        coverage_conditions=CoverageConditions(
            summary="Five or more units",
            geography=Geography("city", "Los Angeles, CA"),
            min_units=5,
        )
    )
    rows = evaluate_address(address, stack_for(address), [covered], AS_OF)
    assert rows[0].result == "unknown"
    assert "unit count" in rows[0].explanation.lower()


def test_cutoff_year_is_unknown():
    address = van_nuys()
    address.year_built = 1979
    covered = rule(
        coverage_conditions=CoverageConditions(
            summary="Certificate of occupancy on or before 1979-06-13",
            geography=Geography("city", "Los Angeles, CA"),
            certificate_of_occupancy_on_or_before="1979-06-13",
        )
    )
    rows = evaluate_address(address, stack_for(address), [covered], AS_OF)
    assert rows[0].result == "unknown"
    assert "1979" in rows[0].explanation


def test_owner_type_is_unknown():
    address = van_nuys()
    covered = rule(
        coverage_conditions=CoverageConditions(
            summary="Owner-occupied exception",
            geography=Geography("city", "Los Angeles, CA"),
            requires_owner_type=True,
        )
    )
    rows = evaluate_address(address, stack_for(address), [covered], AS_OF)
    assert rows[0].result == "unknown"
    assert "owner type" in rows[0].explanation.lower()


def test_stricter_local_rule_supersedes_state_rule():
    address = van_nuys()
    local = rule(team_rule_id="r-city", interaction="supersedes", overrides=["r-state"])
    state = rule(
        team_rule_id="r-state",
        jurisdiction="CA",
        level="state",
        title="Statewide cap",
        coverage_conditions=CoverageConditions("Statewide", Geography("state", "CA")),
    )
    rows = {row.team_rule_id: row for row in evaluate_address(address, stack_for(address), [local, state], AS_OF)}
    assert rows["r-city"].result == "applies"
    assert rows["r-state"].result == "superseded"


def test_default_envelope_uses_as_of_date(tmp_path: Path):
    address = van_nuys()
    stack = stack_for(address)
    envelope = build_lookups([address], {address.address_id: stack}, [rule()], AS_OF)
    assert envelope["as_of"] == "2026-10-01"
    assert list(envelope["lookups"]) == ["A9001"]
    assert envelope["lookups"]["A9001"][0]["result"] == "applies"
    output = tmp_path / "lookups.json"
    output.write_text('{"as_of":"1999-01-01","lookups":{}}', encoding="utf-8")
    from navigator.coverage import write_lookups

    write_lookups(envelope, output, replace=True)
    assert json.loads(output.read_text(encoding="utf-8"))["as_of"] == "2026-10-01"


def test_cached_geocode_does_not_call_census(tmp_path: Path, monkeypatch):
    from navigator.geocode import geocode_addresses

    address = van_nuys()
    cache = tmp_path / "geocodes.json"
    cache.write_text(
        json.dumps(
            {
                "geocodes": {
                    address.address_id: {
                        "address_id": address.address_id,
                        "match_status": "matched",
                        "legal_state": "CA",
                        "legal_county": "Los Angeles",
                        "legal_city": "Los Angeles",
                        "postal_city": "Van Nuys",
                        "retrieved_at": "2026-10-01T00:00Z",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def forbid_network(*_args, **_kwargs):
        raise AssertionError("cached geocodes must not call Census")

    monkeypatch.setattr("urllib.request.urlopen", forbid_network)
    saved = geocode_addresses([address], cache, refresh=False)
    assert saved[address.address_id]["legal_city"] == "Los Angeles"


def test_demo_page_states_it_is_not_legal_advice():
    html = Path("src/navigator/demo/index.html").read_text(encoding="utf-8")
    assert "Not legal advice" in html
    assert "Not a compliance certification" in html
    assert 'id="as-of"' in html
    assert 'id="address"' in html
    assert "No supplied rule applies" in html
