# Contract: Address lookups

**File**: `output/lookups.json`  
**Template**: `data_and_code_base/submission_templates/lookups.json`

## Envelope

```json
{
  "as_of": "2026-10-01",
  "lookups": {
    "A0001": [
      {
        "team_rule_id": "r-0007",
        "result": "applies",
        "explanation": "Why this result was reached.",
        "conflict_flag": false
      }
    ]
  }
}
```

## Required contents

- `as_of` for the default file is `2026-10-01`.
- `lookups` has exactly the address ids in `data_and_code_base/data/sample_addresses.csv`. No extra ids.
- `result` is `applies`, `unknown`, `superseded`, `not_yet_effective`, or `pending`.
- `explanation` is a non-empty plain-language sentence. When `result` is `unknown`, the sentence names the missing fact.
- `team_rule_id` exists in `output/rules.json`.
- A rule that does not cover the address is absent.
- No Santa Ana `team_rule_id` appears on any address.
- No lookup lists `MA-RENT-P1` as `applies`.

## Jurisdiction

City rules are evaluated against `output/geocodes.json` `legal_city`, not against `postal_city`. State rules are evaluated against `legal_state`.

## Date gate

The default file uses 2026-10-01. A caller may request another date. The response uses the same envelope and the date gate in `data-model.md`. T1 and T3 are those calls:

| Call | Expected result |
|---|---|
| `CA-ALG-01` at 2025-12-31 | `not_yet_effective` on every California address |
| `CA-ALG-01` at 2026-01-02 | `applies` on every California address |
| `NJ-ALG-01` at 2026-10-01 | `not_yet_effective` on every New Jersey address |
| `NJ-ALG-01` at 2027-07-02 | `applies` on every New Jersey address, and `conflict_flag` true for Jersey City and Hoboken |

## Missing facts

| Condition | Result |
|---|---|
| Unit test and `units` empty | `unknown`, explanation names unit count |
| Certificate-of-occupancy cutoff and `year_built` empty | `unknown`, explanation names certificate of occupancy |
| `year_built` equals the cutoff year | `unknown`, explanation names the cutoff year |
| `requires_owner_type` true | `unknown`, explanation names owner type |
| `match_status` `unmatched` and the rule is a city rule | `unknown`, explanation names the unresolved legal city |
| `match_status` `unincorporated` and the rule is a city rule | Omitted |
