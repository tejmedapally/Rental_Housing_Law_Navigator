# Contract: Rule catalog

**File**: `output/rules.json`  
**Schema**: `data_and_code_base/schema/rule_record.schema.json`  
**Template**: `data_and_code_base/submission_templates/rules.json`

## Envelope

```json
{ "rules": [ { } ] }
```

Every object in `rules` validates against the schema. Additional fields are not required and are not used by the lookup.

## Verifier

A record is rejected when any of the following is true:

- `quoted_span` is shorter than 20 characters.
- `quoted_span` is not an exact slice of `data_and_code_base/corpus/text/{source_doc_id}.txt` after the `SOURCE` and `RETRIEVED` header. Matching may collapse whitespace to locate the slice. The stored value is the file slice.
- `source_doc_id` is missing from the manifest, or that row has no text file.
- `source_url` differs from the manifest URL for that `doc_id`.
- `category`, `level`, or `status` is outside the schema enums.
- `team_rule_id` is duplicated.
- `effective_date` is present and does not occur in `quoted_span`.
- `key_value` states a 2026 California screening-fee dollar amount that the quoted span does not contain.

## Coverage object

When `coverage_conditions` is an object, it uses the shape in `data-model.md`. The schema accepts that object. A string is valid JSON and is not accepted by this project's verifier, because the lookup cannot re-parse prose.

## Identifiers

These `team_rule_id` values are reserved for the change tests:

| Id | Rule |
|---|---|
| `CA-ALG-01` | California AB 325 / SB 763 algorithmic-pricing rule |
| `HOB-ALG-01` | Hoboken local algorithmic ban |
| `JC-ALG-01` | Jersey City local algorithmic ban |
| `NJ-ALG-01` | New Jersey FAIR Act |
| `MA-ALG-P1` | Massachusetts S.2983 |
| `MA-ALG-P2` | Massachusetts H.5222 |
| `MA-RENT-P1` | Massachusetts rent-control ballot question |

Other ids match `r-` plus four digits.

## Catalog invariants

- At least one Santa Ana city rule is present.
- No rule cites a link-only `doc_id`.
- `MA-RENT-P1` has `status` `failed`.
- `MA-ALG-P1` and `MA-ALG-P2` have `status` `pending`.
- `NJ-ALG-01` has `status` `not_yet_effective` as of 2026-10-01, and `conflict_flag` true, with `JC-ALG-01` and `HOB-ALG-01` named in the note.
- Berkeley's algorithmic ban and Los Angeles's rent-formula rule have `conflict_flag` true when the corpus contains two published dates.
