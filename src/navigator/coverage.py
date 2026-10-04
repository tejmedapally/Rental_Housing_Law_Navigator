"""Decide which rules apply to one address on one date."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from navigator.audit import AuditRecord, append_audit
from navigator.errors import CommandError
from navigator.geocode import stack_from_dict
from navigator.models import CoverageConditions, Geography, JurisdictionStack, LookupResult, RuleRecord, SampleAddress

DEFAULT_AS_OF = "2026-10-01"


def evaluate_address(
    address: SampleAddress,
    stack: JurisdictionStack,
    rules: list[RuleRecord],
    as_of: str,
    audit_path: Path | None = None,
) -> list[LookupResult]:
    """Return listed results. Rules that do not cover the address are omitted."""

    decisions: list[tuple[RuleRecord, LookupResult | None, str]] = []
    for rule in rules:
        result, reason = _decide(address, stack, rule, as_of)
        decisions.append((rule, result, reason))
    _apply_supersession(decisions)
    listed: list[LookupResult] = []
    for rule, result, reason in decisions:
        if audit_path is not None:
            append_audit(
                AuditRecord(
                    address_id=address.address_id,
                    as_of=as_of,
                    team_rule_id=rule.team_rule_id,
                    result=result.result if result is not None else "omitted",
                    reason=reason,
                    source_doc_id=rule.source_doc_id or "",
                    source_retrieved_at="",
                    quoted_span=rule.quoted_span,
                ),
                audit_path,
            )
        if result is not None:
            listed.append(result)
    return listed


def build_lookups(
    addresses: list[SampleAddress],
    stacks: dict[str, JurisdictionStack | dict],
    rules: list[RuleRecord],
    as_of: str,
    audit_path: Path | None = None,
) -> dict:
    lookups: dict[str, list[dict]] = {}
    for address in addresses:
        raw_stack = stacks.get(address.address_id)
        stack = _coerce_stack(address, raw_stack)
        rows = evaluate_address(address, stack, rules, as_of, audit_path=audit_path)
        lookups[address.address_id] = [
            {
                "team_rule_id": row.team_rule_id,
                "result": row.result,
                "explanation": row.explanation,
                "conflict_flag": row.conflict_flag,
            }
            for row in rows
        ]
    return {"as_of": as_of, "lookups": lookups}


def write_lookups(envelope: dict, path: Path, replace: bool = True) -> None:
    """Write the lookup file. A non-default as-of date passes replace=False and leaves the file alone."""

    if not replace:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_lookup(argv: list[str]) -> int:
    from navigator.corpus import load_addresses, repo_root

    options = _parse_lookup_args(argv)
    root = repo_root()
    as_of = options["as_of"] or DEFAULT_AS_OF
    rules_path = options["rules"] or (root / "output" / "rules.json")
    geocode_path = options["geocodes"] or (root / "output" / "geocodes.json")
    output_path = options["output"] or (root / "output" / "lookups.json")
    if not rules_path.is_file():
        raise CommandError(f"Rules file not found: {rules_path}")
    if not geocode_path.is_file():
        raise CommandError(f"Geocode cache not found: {geocode_path}")
    addresses = load_addresses(root) if options["sample"] is None else _load_sample(options["sample"])
    rules = load_rules(rules_path)
    geocodes = json.loads(geocode_path.read_text(encoding="utf-8")).get("geocodes") or {}
    envelope = build_lookups(addresses, geocodes, rules, as_of, audit_path=root / "output" / "audit.jsonl")
    replace = as_of == DEFAULT_AS_OF
    write_lookups(envelope, output_path, replace=replace)
    if not replace:
        print(json.dumps(envelope, ensure_ascii=False))
    return 0


def load_rules(path: Path) -> list[RuleRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [rule_from_dict(item) for item in payload.get("rules") or []]


def rule_from_dict(data: dict) -> RuleRecord:
    coverage = data.get("coverage_conditions")
    parsed = None
    if isinstance(coverage, dict):
        geography = coverage.get("geography") or {}
        parsed = CoverageConditions(
            summary=str(coverage.get("summary") or ""),
            geography=Geography(str(geography.get("level") or ""), str(geography.get("name") or "")),
            min_units=coverage.get("min_units"),
            max_units=coverage.get("max_units"),
            certificate_of_occupancy_on_or_before=coverage.get("certificate_of_occupancy_on_or_before"),
            requires_owner_type=bool(coverage.get("requires_owner_type", False)),
        )
    return RuleRecord(
        team_rule_id=data["team_rule_id"],
        jurisdiction=data["jurisdiction"],
        level=data["level"],
        category=data["category"],
        status=data["status"],
        title=data["title"],
        requirement=data["requirement"],
        citation=data["citation"],
        source_url=data["source_url"],
        quoted_span=data["quoted_span"],
        key_value=data.get("key_value"),
        coverage_conditions=parsed,
        exemptions=data.get("exemptions"),
        overrides=list(data.get("overrides") or []),
        interaction=data.get("interaction"),
        effective_date=data.get("effective_date"),
        source_doc_id=data.get("source_doc_id"),
        confidence=data.get("confidence"),
        conflict_flag=bool(data.get("conflict_flag", False)),
        conflict_note=data.get("conflict_note"),
    )


def _decide(
    address: SampleAddress,
    stack: JurisdictionStack,
    rule: RuleRecord,
    as_of: str,
) -> tuple[LookupResult | None, str]:
    if rule.status == "failed":
        return None, "failed"
    geography = _geography(rule, stack)
    if geography == "omit":
        return None, "outside_jurisdiction"
    if geography == "unresolved":
        return _row(rule, stack, "unknown", "The legal city could not be resolved, so this city rule is unknown."), "city_unresolved"
    if rule.status == "pending":
        return _row(rule, stack, "pending", f"{rule.title} is pending and is not in force."), "pending"
    if _before_effective(rule, as_of):
        return _row(rule, stack, "not_yet_effective", f"{rule.title} is not yet effective on {as_of}."), "before_effective_date"
    covered, reason, explanation = _coverage(address, rule)
    if covered == "omit":
        return None, reason
    if covered == "unknown":
        return _row(rule, stack, "unknown", explanation), reason
    return _row(rule, stack, "applies", rule.requirement), "eligible"


def _apply_supersession(decisions: list[tuple[RuleRecord, LookupResult | None, str]]) -> None:
    by_id = {rule.team_rule_id: (rule, result) for rule, result, _reason in decisions}
    for rule, result, _reason in decisions:
        if result is None or result.result != "applies" or rule.interaction != "supersedes":
            continue
        for other_id in rule.overrides:
            other = by_id.get(other_id)
            if other is None or other[1] is None or other[1].result != "applies":
                continue
            other[1].result = "superseded"
            other[1].explanation = f"Superseded by {rule.team_rule_id}, which applies to this address."
            for index, (item_rule, item_result, item_reason) in enumerate(decisions):
                if item_rule.team_rule_id == other_id:
                    decisions[index] = (item_rule, item_result, "superseded_by")


def _geography(rule: RuleRecord, stack: JurisdictionStack) -> str:
    if rule.level == "state":
        return "match" if stack.legal_state.upper() == rule.jurisdiction.strip().upper() else "omit"
    city, _state = _split_jurisdiction(rule.jurisdiction)
    if city == "santa ana" and _normalize_city(stack.legal_city or "") != "santa ana":
        return "omit"
    if stack.match_status == "unincorporated":
        return "omit"
    if stack.match_status == "unmatched" or not stack.legal_city:
        return "unresolved"
    city, state = _split_jurisdiction(rule.jurisdiction)
    if _normalize_city(stack.legal_city) == city and stack.legal_state.upper() == state:
        return "match"
    return "omit"


def _coverage(address: SampleAddress, rule: RuleRecord) -> tuple[str, str, str]:
    coverage = rule.coverage_conditions
    if coverage is None:
        return "applies", "eligible", ""
    if coverage.min_units is not None or coverage.max_units is not None:
        if address.units is None:
            return "unknown", "missing_units", "Coverage depends on unit count, which is missing from the sample."
        if coverage.min_units is not None and address.units < coverage.min_units:
            return "omit", "outside_jurisdiction", ""
        if coverage.max_units is not None and address.units > coverage.max_units:
            return "omit", "outside_jurisdiction", ""
    if coverage.requires_owner_type:
        return "unknown", "owner_type", "Coverage depends on owner type, which is missing from the sample."
    cutoff = coverage.certificate_of_occupancy_on_or_before
    if cutoff:
        if address.year_built is None:
            return "unknown", "missing_year", "Coverage depends on the certificate of occupancy, which is missing from the sample."
        cutoff_year = int(cutoff.split("-")[0])
        if address.year_built == cutoff_year:
            return "unknown", "co_cutoff_year", f"The construction year {address.year_built} is the certificate-of-occupancy cutoff year, so coverage is unknown."
        if address.year_built > cutoff_year:
            return "omit", "outside_jurisdiction", ""
    return "applies", "eligible", ""


def _before_effective(rule: RuleRecord, as_of: str) -> bool:
    if rule.effective_date:
        return _as_date(as_of) < _as_date(rule.effective_date)
    return rule.status == "not_yet_effective"


def _row(rule: RuleRecord, stack: JurisdictionStack, result: str, explanation: str) -> LookupResult:
    return LookupResult(
        team_rule_id=rule.team_rule_id,
        result=result,
        explanation=explanation,
        conflict_flag=_conflict(rule, stack),
    )


def _conflict(rule: RuleRecord, stack: JurisdictionStack) -> bool:
    if not rule.conflict_flag:
        return False
    note = rule.conflict_note or ""
    if not note or not stack.legal_city:
        return True
    return stack.legal_city.casefold() in note.casefold()


def _coerce_stack(address: SampleAddress, raw: JurisdictionStack | dict | None) -> JurisdictionStack:
    if isinstance(raw, JurisdictionStack):
        return raw
    if isinstance(raw, dict):
        return stack_from_dict(raw)
    return JurisdictionStack(
        address_id=address.address_id,
        match_status="unmatched",
        legal_state=address.state,
        legal_county=None,
        legal_city=None,
        postal_city=address.postal_city,
        retrieved_at="",
    )


def _split_jurisdiction(jurisdiction: str) -> tuple[str, str]:
    city, state = jurisdiction.rsplit(",", 1)
    return _normalize_city(city), state.strip().upper()


def _normalize_city(name: str) -> str:
    cleaned = name.strip()
    if cleaned.casefold().endswith(" city"):
        cleaned = cleaned[: -len(" city")]
    return cleaned.casefold()


def _as_date(value: str) -> date:
    parts = value.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return date(year, month, day)


def _load_sample(path: Path) -> list[SampleAddress]:
    import csv

    addresses = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            addresses.append(
                SampleAddress(
                    address_id=row["address_id"].strip(),
                    street_address=row["street_address"].strip(),
                    postal_city=row["postal_city"].strip(),
                    state=row["state"].strip(),
                    zip=row["zip"].strip(),
                    year_built=int(row["year_built"]) if row["year_built"].strip() else None,
                    units=int(row["units"]) if row["units"].strip() else None,
                    use_code=row.get("use_code", "").strip(),
                    use_description=row.get("use_description", "").strip(),
                    source_dataset=row.get("source_dataset", "").strip(),
                    retrieved_at=row.get("retrieved_at", "").strip(),
                )
            )
    return addresses


def _parse_lookup_args(argv: list[str]) -> dict:
    options: dict[str, Path | str | None] = {
        "as_of": None,
        "rules": None,
        "geocodes": None,
        "output": None,
        "sample": None,
    }
    flags = {
        "--as-of": "as_of",
        "--rules": "rules",
        "--geocodes": "geocodes",
        "--output": "output",
        "--sample": "sample",
    }
    index = 0
    while index < len(argv):
        flag = argv[index]
        if flag not in flags or index + 1 >= len(argv):
            raise CommandError(
                "usage: python -m navigator lookup --as-of YYYY-MM-DD [--rules PATH] [--geocodes PATH] [--output PATH]"
            )
        value = argv[index + 1]
        key = flags[flag]
        options[key] = value if key == "as_of" else Path(value)
        index += 2
    return options
