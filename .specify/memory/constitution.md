<!--
Sync Impact Report
- Version change: unreleased template → 1.0.0
- Modified principles:
  - [PRINCIPLE_1_NAME] → I. Traceable Citations
  - [PRINCIPLE_2_NAME] → II. Automated Extraction
  - [PRINCIPLE_3_NAME] → III. Unknown Over Guessing (NON-NEGOTIABLE)
  - [PRINCIPLE_4_NAME] → IV. Honest Legal Status
  - [PRINCIPLE_5_NAME] → V. Public Data and Not Legal Advice
- Added sections:
  - Scope and Submission Contract
  - Quality Gates
- Removed sections: none
- Follow-up TODOs: none
-->

# Rental Housing Law Navigator Constitution

## Core Principles

### I. Traceable Citations

Every rule record and every address answer MUST cite the source document, a quoted span copied from that document, the source URL, the retrieval date, and the query as-of date. A citation MUST match text the system actually read in the supplied corpus or another allowed public source. The system MUST NOT invent rules, citations, or quoted spans.

Rationale: An address-level housing answer is usable only when another person can reproduce it from the cited text.

### II. Automated Extraction

Rule records MUST be produced by an automated pipeline that reads the supplied corpus. Hand-authored rule text MUST NOT be the source of truth. The extraction pipeline MUST be reproducible and demonstrable in the live demo. Human review MAY flag conflicts and correct pipeline errors. Every correction MUST remain tied to a source document and a quoted span.

Rationale: The challenge evaluates whether the system reads the law.

### III. Unknown Over Guessing (NON-NEGOTIABLE)

When coverage depends on a fact the supplied data does not contain, the lookup result MUST be `unknown`, with an explanation of the missing fact. The system MUST NOT infer that fact. Year built MUST NOT be treated as a certificate-of-occupancy date. A building in a cutoff year MUST be `unknown`. Owner-type exceptions MUST be `unknown` because the sample has no owner names. Rules that do not apply MUST be omitted from the lookup.

Rationale: A missing fact is an explicit gap. Filling it in is a wrong answer.

### IV. Honest Legal Status

Each rule MUST carry one status: `in_force`, `not_yet_effective`, `pending`, or `failed`, evaluated against the query date. Lookup results MUST use only `applies`, `unknown`, `superseded`, `not_yet_effective`, or `pending`. Enacted law, pending bills, future effective dates, and failed measures MUST stay distinct. Overlapping state and local rules MUST record which rule supersedes or yields. Possible preemption MUST set `conflict_flag` for human review. The default query date is 2026-10-01 unless a test names another date.

Rationale: The change tests check dates, city boundaries, pending bills, and failed proposals as separate outcomes.

### V. Public Data and Not Legal Advice

The system MUST use only public data and the supplied starter pack. It MUST NOT use customer, resident, or pricing data. It MUST NOT bulk-scrape sites whose terms forbid scraping. Link-only publisher pages stay link-only. Every user-facing interface MUST state that the output is not legal advice and not a compliance certification. The system MUST NOT suggest ways to avoid a rule.

Rationale: The prototype explains public law. It does not advise, certify, or collect private housing data.

## Scope and Submission Contract

The corpus covers California, New Jersey, and Massachusetts, and the cities Los Angeles, San Francisco, San Diego, Berkeley, Santa Ana, Jersey City, Hoboken, Newark, Boston, and Cambridge. Santa Ana rules are extraction-only: the address sample has no Santa Ana rows.

Rule categories are limited to `rent_increase_limits`, `just_cause_eviction`, `security_deposits`, `application_screening_fees`, `screening_restrictions`, and `algorithmic_rent_setting`. Jurisdiction level is `state` or `city`. `postal_city` is a mailing city. Address lookup MUST resolve the legal state, county, and city before testing coverage.

A complete submission MUST include:

- `rules.json`: rule records valid against `schema/rule_record.schema.json`, including a `quoted_span` of at least 20 characters.
- `lookups.json`: an as-of date and a lookup entry for every sample address.
- `changes.json`: affected address ids, conflict-flag address ids, and notes for each supplied change test.
- A live demo of the extraction pipeline and a one-page method note.
- An audit log sufficient for another person to reproduce a result.

Module priority is fixed. Modules A and B (extraction, jurisdiction resolution, and citations) come before Module C (change tracking and plain language). Stretch goals come only after those. Stretch goals are a Spanish plain-language view, confidence indicators, one new jurisdiction on the same pipeline, and an audit view.

## Quality Gates

A submission is compliant only when all of the following hold:

- Every rule record validates against the rule schema, and its `quoted_span` appears in the cited source text.
- `lookups.json` covers all 500 sample addresses for as-of 2026-10-01.
- Change tests T1 through T5 match `dev/change_tests.json`:
  - T1: California AB 325 / SB 763 is `not_yet_effective` on 2025-12-31 and `applies` on 2026-01-02 for every California address.
  - T2: The Hoboken algorithmic ban applies only in Hoboken, and the Jersey City ban only in Jersey City. Neither applies in Newark.
  - T3: The New Jersey FAIR Act is `not_yet_effective` on 2026-10-01 and `applies` on 2027-07-02 for every New Jersey address. Jersey City and Hoboken addresses carry a conflict flag.
  - T4: Massachusetts S.2983 and H.5222 are `pending`. The affected set, if enacted, is every Massachusetts address.
  - T5: The Massachusetts rent-control ballot question is `failed`. No rent cap is reported for Boston or Cambridge. The affected set is empty.
- Known open questions stay flagged. These include Berkeley's two published algorithmic-ban effective dates, possible FAIR Act preemption, Los Angeles's two published RSO effective dates, and the absence of a single official 2026 California screening-fee dollar figure.
- Where a coverage test depends on a missing building fact listed in the participant guide (year built, unit count, certificate of occupancy, or owner type), the result is `unknown`.

## Governance

This constitution supersedes conflicting local practice for this project. Specs, plans, and tasks MUST comply with it. A review MUST reject output that invents a citation, guesses a missing fact, presents results as legal advice, or fails schema validation or tests T1–T5.

Amendments require a short written rationale, a Sync Impact Report, and a version bump before the change is treated as binding:

- MAJOR: remove or redefine a principle so that existing specs can no longer comply.
- MINOR: add a principle or materially expand a requirement.
- PATCH: clarify wording without changing obligations.

The ratification date is the date of first adoption. The last-amended date changes only when the constitution text changes. Runtime guidance lives in `data_and_code_base/README.md` and the challenge brief. If those documents conflict with this constitution, this constitution wins, and the conflict MUST be resolved by amendment or by correcting the downstream spec.

**Version**: 1.0.0 | **Ratified**: 2026-10-03 | **Last Amended**: 2026-10-03
