"""Shared records for rules, addresses, jurisdictions, and lookup results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Geography:
    """Where a coverage test applies."""

    level: str
    name: str


@dataclass
class CoverageConditions:
    """Structured coverage test stored on a rule record."""

    summary: str
    geography: Geography
    min_units: int | None = None
    max_units: int | None = None
    certificate_of_occupancy_on_or_before: str | None = None
    requires_owner_type: bool = False


@dataclass
class RuleRecord:
    """One housing rule extracted from a corpus document."""

    team_rule_id: str
    jurisdiction: str
    level: str
    category: str
    status: str
    title: str
    requirement: str
    citation: str
    source_url: str
    quoted_span: str
    key_value: str | None = None
    coverage_conditions: CoverageConditions | None = None
    exemptions: str | None = None
    overrides: list[str] = field(default_factory=list)
    interaction: str | None = None
    effective_date: str | None = None
    source_doc_id: str | None = None
    confidence: float | None = None
    conflict_flag: bool = False
    conflict_note: str | None = None


@dataclass
class SampleAddress:
    """One multifamily property from the public assessor sample."""

    address_id: str
    street_address: str
    postal_city: str
    state: str
    zip: str
    year_built: int | None
    units: int | None
    use_code: str
    use_description: str
    source_dataset: str
    retrieved_at: str


@dataclass
class JurisdictionStack:
    """Legal state, county, and city resolved for one sample address."""

    address_id: str
    match_status: str
    legal_state: str
    legal_county: str | None
    legal_city: str | None
    postal_city: str
    retrieved_at: str
    raw_match: dict | None = None


@dataclass
class LookupResult:
    """One rule's result for one address on one date."""

    team_rule_id: str
    result: str
    explanation: str
    conflict_flag: bool = False
