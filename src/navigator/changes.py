"""Build the T1–T5 change report from cached legal cities and states."""

from __future__ import annotations

import json
from pathlib import Path

from navigator.corpus import repo_root
from navigator.errors import CommandError

_NOTES = {
    "T1": (
        "CA-ALG-01 is not yet effective on 2025-12-31 and applies on 2026-01-02 "
        "for every California address."
    ),
    "T2": (
        "The Hoboken ban (HOB-ALG-01) and the Jersey City ban (JC-ALG-01) are the "
        "two local bans. Neither applies in Newark."
    ),
    "T3": (
        "NJ-ALG-01 is not yet effective on 2026-10-01 and applies on 2027-07-02 "
        "for every New Jersey address. Jersey City and Hoboken addresses are flagged "
        "for human review because the state law may preempt those local bans."
    ),
    "T4": (
        "MA-ALG-P1 and MA-ALG-P2 are both pending and are not in force. This set is "
        "every Massachusetts address that would be affected if the bills were enacted."
    ),
    "T5": (
        "The Massachusetts rent-control ballot question failed. No rent cap is "
        "reported for Boston or Cambridge."
    ),
}
_LOCAL_CITIES = ("Hoboken", "Jersey City")


def build_changes(geocodes: dict[str, dict], tests: list[dict] | None = None) -> dict:
    """Return the T1–T5 envelope. Address lists are sorted and unique."""

    cases = {item["test_id"]: item for item in (tests if tests is not None else load_change_tests())}
    rows = [_row(address_id, record) for address_id, record in geocodes.items()]
    report: dict[str, dict] = {}
    for test_id in ("T1", "T2", "T3", "T4", "T5"):
        case = cases[test_id]
        if case.get("type") == "negative":
            affected: list[str] = []
        elif test_id == "T2":
            affected = _city_ids(rows, _LOCAL_CITIES)
        else:
            affected = _state_ids(rows, case.get("states") or [])
        entry: dict[str, list[str] | str] = {
            "affected_address_ids": affected,
            "notes": _NOTES[test_id],
        }
        if test_id == "T3":
            entry["conflict_flag_address_ids"] = _city_ids(rows, _LOCAL_CITIES)
        report[test_id] = entry
    return report


def load_change_tests(path: Path | None = None) -> list[dict]:
    file_path = path or (repo_root() / "data_and_code_base" / "dev" / "change_tests.json")
    if not file_path.is_file():
        raise CommandError(f"Change tests not found: {file_path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CommandError(f"Change tests must be a list: {file_path}")
    return payload


def write_changes(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_changes(argv: list[str]) -> int:
    options = _parse_changes_args(argv)
    root = repo_root()
    geocode_path = options["geocodes"] or (root / "output" / "geocodes.json")
    output_path = options["output"] or (root / "output" / "changes.json")
    if not geocode_path.is_file():
        raise CommandError(f"Geocode cache not found: {geocode_path}")
    payload = json.loads(geocode_path.read_text(encoding="utf-8"))
    geocodes = payload.get("geocodes") if isinstance(payload, dict) else None
    if not isinstance(geocodes, dict):
        raise CommandError(f"Geocode cache has no geocodes object: {geocode_path}")
    write_changes(build_changes(geocodes), output_path)
    return 0


def _row(address_id: str, record: dict) -> tuple[str, str, str]:
    state = str(record.get("legal_state") or "").strip().upper()
    return address_id, state, _normalize_city(str(record.get("legal_city") or ""))


def _state_ids(rows: list[tuple[str, str, str]], states: list[str]) -> list[str]:
    wanted = {state.strip().upper() for state in states}
    return sorted({address_id for address_id, state, _city in rows if state in wanted})


def _city_ids(rows: list[tuple[str, str, str]], cities: tuple[str, ...]) -> list[str]:
    wanted = {_normalize_city(city) for city in cities}
    return sorted({address_id for address_id, _state, city in rows if city in wanted})


def _normalize_city(name: str) -> str:
    cleaned = name.strip()
    if cleaned.casefold().endswith(" city"):
        cleaned = cleaned[: -len(" city")].strip()
    return cleaned.casefold()


def _parse_changes_args(argv: list[str]) -> dict[str, Path | None]:
    options: dict[str, Path | None] = {"geocodes": None, "output": None}
    flags = {"--geocodes": "geocodes", "--output": "output"}
    index = 0
    while index < len(argv):
        flag = argv[index]
        if flag not in flags or index + 1 >= len(argv):
            raise CommandError("usage: python -m navigator changes [--geocodes PATH] [--output PATH]")
        options[flags[flag]] = Path(argv[index + 1])
        index += 2
    return options
