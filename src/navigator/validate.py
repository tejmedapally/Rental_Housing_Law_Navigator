"""Check the catalog, the 500 lookups, and the T1–T5 sets."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from navigator.changes import build_changes
from navigator.corpus import SourceDocument, load_addresses, load_documents, repo_root
from navigator.errors import CommandError
from navigator.extract import exact_slice
from navigator.method_note import write_method_note

_REQUIRED_STATUS = {
    "MA-ALG-P1": "pending",
    "MA-ALG-P2": "pending",
}


def catalog_problems(rules: list[dict], link_only_ids: set[str] | None = None) -> list[str]:
    """Return human-readable problems. An empty list means the catalog checks pass."""

    blocked = link_only_ids or set()
    problems: list[str] = []
    validator = Draft202012Validator(_rule_schema())
    for index, rule in enumerate(rules):
        label = str(rule.get("team_rule_id") or f"rule {index}")
        for error in sorted(validator.iter_errors(rule), key=lambda item: list(item.path)):
            problems.append(f"{label}: {error.message}")
        doc_id = rule.get("source_doc_id")
        if doc_id in blocked:
            problems.append(f"{doc_id} is link-only and cannot support {label}")
    if not any(_is_santa_ana(rule) for rule in rules):
        problems.append("Catalog is missing a Santa Ana city rule")
    by_id = {rule.get("team_rule_id"): rule for rule in rules}
    for rule_id, status in _REQUIRED_STATUS.items():
        rule = by_id.get(rule_id)
        if rule is None or rule.get("status") != status:
            problems.append(f"{rule_id} must be present with status {status}")
    rent = by_id.get("MA-RENT-P1")
    if rent is not None and rent.get("status") != "failed":
        problems.append("MA-RENT-P1 must have status failed")
    return problems


def _is_santa_ana(rule: dict) -> bool:
    return rule.get("level") == "city" and "Santa Ana" in str(rule.get("jurisdiction") or "")


def _rule_schema() -> dict:
    path = repo_root() / "data_and_code_base" / "schema" / "rule_record.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


_RESULTS = {"applies", "unknown", "superseded", "not_yet_effective", "pending"}
_TESTS = ("T1", "T2", "T3", "T4", "T5")


def submission_problems(
    rules: list[dict],
    lookups: dict,
    changes: dict,
    geocodes: dict[str, dict],
    documents: list[SourceDocument],
    address_ids: list[str],
    link_only_ids: set[str] | None = None,
) -> list[str]:
    """Return every submission problem. An empty list means validate can exit 0."""

    problems = catalog_problems(rules, link_only_ids)
    problems.extend(span_problems(rules, documents))
    problems.extend(lookup_problems(lookups, address_ids, rules))
    problems.extend(change_set_problems(changes, geocodes))
    return problems


def span_problems(rules: list[dict], documents: list[SourceDocument]) -> list[str]:
    """Reject a quoted span that is not the captured file slice."""

    by_id = {document.doc_id: document for document in documents}
    problems: list[str] = []
    for index, rule in enumerate(rules):
        label = str(rule.get("team_rule_id") or f"rule {index}")
        doc_id = str(rule.get("source_doc_id") or "").strip()
        document = by_id.get(doc_id)
        if document is None:
            problems.append(f"{label}: source_doc_id {doc_id or '(missing)'} has no captured text")
            continue
        if str(rule.get("source_url") or "").strip() != document.url:
            problems.append(f"{label}: source_url does not match the manifest")
        quoted = rule.get("quoted_span")
        if not isinstance(quoted, str) or len(quoted) < 20 or exact_slice(document.text, quoted) != quoted:
            problems.append(f"{label}: quoted_span is not an exact slice of {doc_id}")
            continue
        effective_date = rule.get("effective_date")
        if effective_date and str(effective_date) not in quoted:
            problems.append(f"{label}: effective_date does not occur in quoted_span")
    return problems


def lookup_problems(lookups: dict, address_ids: list[str], rules: list[dict]) -> list[str]:
    """Require every sample id, no Santa Ana hit, and no applying failed rent-control question."""

    problems: list[str] = []
    if lookups.get("as_of") != "2026-10-01":
        problems.append("lookups as_of must be 2026-10-01")
    rows = lookups.get("lookups")
    if not isinstance(rows, dict):
        return problems + ["lookups must contain a lookups object"]
    expected = set(address_ids)
    actual = set(rows)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        problems.append(f"lookups is missing {len(missing)} sample address ids, starting with {missing[:5]}")
    if extra:
        problems.append(f"lookups has address ids that are not in the sample, starting with {extra[:5]}")
    known_ids = {rule.get("team_rule_id") for rule in rules}
    santa_ana_ids = {rule.get("team_rule_id") for rule in rules if _is_santa_ana(rule)}
    for address_id, entries in rows.items():
        if not isinstance(entries, list):
            problems.append(f"{address_id}: lookup entries must be a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append(f"{address_id}: a lookup entry is not an object")
                continue
            rule_id = entry.get("team_rule_id")
            if rule_id not in known_ids:
                problems.append(f"{address_id}: {rule_id} is not in the catalog")
            if rule_id in santa_ana_ids:
                problems.append(f"{address_id}: Santa Ana rule {rule_id} must not appear on a sample address")
            if rule_id == "MA-RENT-P1" and entry.get("result") == "applies":
                problems.append(f"{address_id}: MA-RENT-P1 must not apply")
            if entry.get("result") not in _RESULTS:
                problems.append(f"{address_id}: {rule_id} has a result outside the allowed values")
            if not str(entry.get("explanation") or "").strip():
                problems.append(f"{address_id}: {rule_id} is missing an explanation")
    return problems


def change_set_problems(changes: dict, geocodes: dict[str, dict]) -> list[str]:
    """Compare T1–T5 address sets with the legal cities and states."""

    if not isinstance(changes, dict):
        return ["changes.json must be an object"]
    expected = build_changes(geocodes)
    problems: list[str] = []
    for test_id in _TESTS:
        actual = changes.get(test_id)
        want = expected[test_id]
        if not isinstance(actual, dict):
            problems.append(f"{test_id} is missing")
            continue
        if actual.get("affected_address_ids") != want["affected_address_ids"]:
            problems.append(f"{test_id} affected_address_ids do not match the legal cities and states")
        want_flags = want.get("conflict_flag_address_ids")
        actual_flags = actual.get("conflict_flag_address_ids")
        if want_flags is None:
            if actual_flags not in (None, []):
                problems.append(f"{test_id} must not list conflict_flag_address_ids")
        elif actual_flags != want_flags:
            problems.append(f"{test_id} conflict_flag_address_ids do not match Jersey City and Hoboken")
        notes = str(actual.get("notes") or "")
        if not notes.strip():
            problems.append(f"{test_id} notes are empty")
            continue
        lowered = notes.casefold()
        if test_id == "T2" and not ("hoboken" in lowered and "jersey city" in lowered and "newark" in lowered):
            problems.append("T2 notes must name both local bans and Newark")
        if test_id == "T4" and not ("pending" in lowered and "enacted" in lowered):
            problems.append("T4 notes must say both bills are pending and name who would be affected if enacted")
        if test_id == "T5" and not ("failed" in lowered and "boston" in lowered and "cambridge" in lowered):
            problems.append("T5 notes must say the ballot question failed and name Boston and Cambridge")
    return problems


def run_validate(argv: list[str] | None = None) -> int:
    """Exit 0 only when the catalog, lookups, and change sets pass. Write the method note on success."""

    options = _parse_validate_args(list(argv or []))
    root = repo_root()
    rules_path = options["rules"] or (root / "output" / "rules.json")
    lookups_path = options["lookups"] or (root / "output" / "lookups.json")
    changes_path = options["changes"] or (root / "output" / "changes.json")
    geocode_path = options["geocodes"] or (root / "output" / "geocodes.json")
    for label, path in (
        ("Rules", rules_path),
        ("Lookups", lookups_path),
        ("Changes", changes_path),
        ("Geocode cache", geocode_path),
    ):
        if not path.is_file():
            raise CommandError(f"{label} file not found: {path}")
    rules = json.loads(rules_path.read_text(encoding="utf-8")).get("rules") or []
    lookups = json.loads(lookups_path.read_text(encoding="utf-8"))
    changes = json.loads(changes_path.read_text(encoding="utf-8"))
    geocodes = json.loads(geocode_path.read_text(encoding="utf-8")).get("geocodes") or {}
    addresses = load_addresses(root) if options["sample"] is None else _load_ids(options["sample"])
    problems = submission_problems(
        rules,
        lookups,
        changes,
        geocodes,
        load_documents(root),
        [address.address_id for address in addresses],
        link_only_ids(root),
    )
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    write_method_note(options["method_note"])
    return 0


def link_only_ids(root: Path | None = None) -> set[str]:
    base = root or repo_root()
    path = base / "data_and_code_base" / "corpus" / "corpus_manifest.csv"
    blocked: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("status") or "").strip() == "link-only":
                blocked.add((row.get("doc_id") or "").strip())
    return blocked


def _load_ids(path: Path):
    from navigator.coverage import _load_sample

    return _load_sample(path)


def _parse_validate_args(argv: list[str]) -> dict[str, Path | None]:
    options: dict[str, Path | None] = {
        "rules": None,
        "lookups": None,
        "changes": None,
        "geocodes": None,
        "sample": None,
        "method_note": None,
    }
    flags = {
        "--rules": "rules",
        "--lookups": "lookups",
        "--changes": "changes",
        "--geocodes": "geocodes",
        "--sample": "sample",
        "--method-note": "method_note",
    }
    index = 0
    while index < len(argv):
        flag = argv[index]
        if flag not in flags or index + 1 >= len(argv):
            raise CommandError(
                "usage: python -m navigator validate [--rules PATH] [--lookups PATH] "
                "[--changes PATH] [--geocodes PATH] [--sample PATH] [--method-note PATH]"
            )
        options[flags[flag]] = Path(argv[index + 1])
        index += 2
    return options
