# Data Model: Rental Housing Law Navigator

Field names below are the stored names. The rule record still validates against `data_and_code_base/schema/rule_record.schema.json`.

## Source document

Loaded from `data_and_code_base/corpus/corpus_manifest.csv`. Not rewritten.

| Field | Rules |
|---|---|
| `doc_id` | `D001`–`D087` |
| `jurisdictions` | State code or `City, ST` |
| `url` | Source location copied onto each rule |
| `source_type` | Informational |
| `capture` | `yes` with a text file is readable. Anything else is skipped |
| `retrieved_at` | Copied onto the audit record |
| `text_file` | Path under `corpus/text/`. Empty means no rule text |
| `status` | `ok` is readable. `link-only` and the `D056` manual failure are not fetched |

A document yields zero or more rule records. One statute section can yield more than one rule when it states more than one category.

## Rule record

One extracted rule. Stored in `output/rules.json` under `rules`.

| Field | Rules |
|---|---|
| `team_rule_id` | Unique. Tested rules use the ids in `dev/change_tests.json`. Others use `r-NNNN` |
| `jurisdiction` | `CA`, `NJ`, `MA`, or `City, ST` |
| `level` | `state` or `city` |
| `category` | One of the six schema categories |
| `status` | Status as of 2026-10-01: `in_force`, `not_yet_effective`, `pending`, or `failed` |
| `title` | Short name |
| `requirement` | One or two plain-language sentences |
| `key_value` | Headline number or formula, or null. Null when no single official figure exists |
| `coverage_conditions` | Object defined below, or null when the source states none |
| `exemptions` | Text from the source, or null |
| `overrides` | Other `team_rule_id` values this rule supersedes or yields to |
| `interaction` | `supersedes`, `yields_to`, or null |
| `effective_date` | `YYYY-MM-DD` from the quoted span, or null |
| `citation` | Official cite |
| `source_doc_id` | Manifest `doc_id` |
| `source_url` | Manifest URL |
| `quoted_span` | Exact slice of the text file, length at least 20 |
| `confidence` | Optional number from 0 to 1. The demo does not present it as a product feature |
| `conflict_flag` | True when published dates disagree, preemption is possible, or a headline number is not official |
| `conflict_note` | Why the flag is set, or null |

### Coverage object

```json
{
  "summary": "Plain-language coverage statement",
  "geography": { "level": "city", "name": "Hoboken, NJ" },
  "min_units": null,
  "max_units": null,
  "certificate_of_occupancy_on_or_before": null,
  "requires_owner_type": false
}
```

- `geography.level` is `state` or `city`. `geography.name` matches `jurisdiction`.
- Unit bounds are integers or null. A null bound is not a test.
- `certificate_of_occupancy_on_or_before` is a date or null. The engine never fills it from `year_built`.
- `requires_owner_type` true forces lookup result `unknown` on every sample address.

### Status transitions

`status` is stored as of 2026-10-01. Lookup derives the result for the requested date:

| Stored status | Requested date | Derived gate |
|---|---|---|
| `failed` | any | Not listed as applying. Change-case affected set stays empty |
| `pending` | any | Result `pending` |
| `not_yet_effective` or `in_force`, with `effective_date` | before `effective_date` | `not_yet_effective` |
| `not_yet_effective` or `in_force`, with `effective_date` | on or after `effective_date` | Eligible for coverage testing |
| `in_force`, no `effective_date` | any | Eligible for coverage testing |

Coverage testing runs only after the date gate says the rule is eligible.

## Sample address

Loaded from `data_and_code_base/data/sample_addresses.csv`. Not rewritten.

| Field | Rules |
|---|---|
| `address_id` | `A0001`–`A0500` |
| `street_address`, `postal_city`, `state`, `zip` | Sent to the geocoder. `postal_city` is not the legal city |
| `year_built` | Integer or empty. Empty, or equal to a certificate cutoff year, cannot satisfy that cutoff |
| `units` | Integer or empty. Empty cannot satisfy a unit test |
| `use_code`, `use_description` | Informational. Boston rows whose `use_code` starts with `A/` have no unit count |
| `source_dataset`, `retrieved_at` | Provenance only |

There is no owner field. No later stage adds one.

## Jurisdiction stack

One cached Census match per `address_id` in `output/geocodes.json`.

| Field | Rules |
|---|---|
| `address_id` | Matches the sample |
| `match_status` | `matched`, `unincorporated`, or `unmatched` |
| `legal_state` | From the Census match when matched. Otherwise the sample `state` |
| `legal_county` | From the Census match, or null |
| `legal_city` | Incorporated Place name, or null |
| `postal_city` | Copied from the sample for audit only. Never used as `legal_city` |
| `retrieved_at` | When the geocoder response was saved |
| `raw_match` | The Census address-match object, so a reviewer can see the place name |

Relationship: one sample address has one jurisdiction stack. City rules apply only when `legal_city` plus state equals the rule jurisdiction. State rules apply when `legal_state` equals the rule jurisdiction.

## Lookup result

`output/lookups.json`:

```json
{
  "as_of": "2026-10-01",
  "lookups": {
    "A0001": [
      {
        "team_rule_id": "r-0007",
        "result": "applies",
        "explanation": "Plain-language reason, including any missing fact.",
        "conflict_flag": false
      }
    ]
  }
}
```

- `result` is `applies`, `unknown`, `superseded`, `not_yet_effective`, or `pending`.
- Every `address_id` in the sample is a key, even if its list is empty.
- A rule whose date gate fails as not-yet-effective or pending is listed.
- A rule that fails geography or an affirmative coverage test is omitted.
- A rule that would apply except for a missing fact is `unknown`.
- When `interaction` is `supersedes` and this rule's result is `applies`, each id in `overrides` is listed as `superseded` if that other rule also covers the address.
- `conflict_flag` is true when the rule record is flagged or when test T3 requires a review flag for that city.

## Change case

Input: `data_and_code_base/dev/change_tests.json`. Output: `output/changes.json`, one object per `test_id`.

| Field | Rules |
|---|---|
| `affected_address_ids` | Sample ids whose result for the named rule changes, or would change, as the test describes |
| `conflict_flag_address_ids` | Present for T3. Jersey City and Hoboken ids |
| `notes` | Short reason a reviewer can check |

T1 and T3 compare two as-of dates. T2 compares legal cities on 2026-10-01. T4 lists every Massachusetts sample id because the bills are pending. T5 lists no ids and the Massachusetts rent-cap rule stays `failed`.

## Audit record

One JSON object per line in `output/audit.jsonl`.

| Field | Rules |
|---|---|
| `address_id` | Sample id, or null for a catalog-only event |
| `as_of` | Query date |
| `team_rule_id` | Rule under test |
| `result` | Lookup result, or `omitted` |
| `reason` | One of `eligible`, `outside_jurisdiction`, `before_effective_date`, `pending`, `failed`, `missing_units`, `missing_year`, `co_cutoff_year`, `owner_type`, `city_unresolved`, `superseded_by`, `conflict_review` |
| `source_doc_id` | Manifest id |
| `source_retrieved_at` | From the manifest |
| `quoted_span_sha256` | Hash of the stored span |

A second person can open the rule, the text file, and this line and replay the result.

## Relationships

```text
Source document 1──* Rule record
Sample address 1──1 Jurisdiction stack
Sample address 1──* Lookup result
Rule record 1──* Lookup result
Change case *──* Sample address
Lookup result 1──* Audit record
```
