# Research: Rental Housing Law Navigator

Resolved before design. Each item is a decision the implementation must follow.

## 1. Runtime

- **Decision**: Python 3.13 from the existing `.venv` (`Python 3.13.15`). The system `python` command on this machine is a store alias and is not used.
- **Rationale**: A virtual environment is already present. The workload is file parsing, JSON validation, and a few hundred cached lookups.
- **Alternatives considered**: A new language runtime. Rejected because the repo already has a working 3.13 environment and the starter pack is data, not an application.

## 2. Extraction

- **Decision**: An extractor reads only corpus files whose manifest row has captured text. It proposes rule records, then a verifier accepts a record only when `quoted_span` is at least 20 characters and matches a slice of that file. Whitespace may be collapsed to find the slice; the stored span is the exact slice from the file. Link-only rows, publisher pages, and the failed Massachusetts download (`D056`) are skipped and never fetched.
- **Rationale**: Constitution principle II requires automated reading. Principle I requires a real quotation. Snapping to the file slice keeps the citation honest when a model joins line breaks.
- **Alternatives considered**: Hand-written rule records. Rejected by the constitution. Trusting a model span without a file match. Rejected because a paraphrase would ship as a citation.

## 3. Model access

- **Decision**: The proposer sits behind one interface. When `NAVIGATOR_MODEL_BASE_URL` is set, that interface calls an OpenAI-compatible chat endpoint with the standard library HTTP client. Validated records are written to `output/rules.json`. Lookup, change cases, and the demo page run from that file and do not call a model. A human correction is a second file that may change a record only when the new `quoted_span` still matches the source file.
- **Rationale**: Organizers have not fixed model access. The demo still has to show reading and verification, and the graded outputs have to be reproducible offline.
- **Alternatives considered**: A vendor SDK. Rejected because the event model is undecided and a SDK would lock the pipeline to one host. Re-extracting on every lookup. Rejected because results would change between runs and the demo would depend on the network.

## 4. Legal city

- **Decision**: Resolve each address with the Census single-address geographies service, `https://geocoding.geo.census.gov/geocoder/geographies/address`, benchmark `Public_AR_Current`, vintage `Current_Current`. Read state, county, and Incorporated Place from the JSON match. Cache the result in `output/geocodes.json`. Do not use `postal_city` as the legal city.
- **Rationale**: The participant guide allows this service and asks for incorporated place. The official batch geographies service returns only state, county, tract, and block, so a batch file cannot name the legal city. Five hundred cached single-address calls are within the no-key limit.
- **Alternatives considered**: `POST /geocoder/geographies/addressbatch`. Rejected because that response has no incorporated place. Falling back to `postal_city` when a match fails. Rejected by the spec. A TIGER/Line spatial join. Allowed, and unnecessary once the single-address response already names the place.

## 5. Unmatched and unincorporated addresses

- **Decision**: A Census match with no Incorporated Place is unincorporated: city ordinances do not apply, and county and state still do. A failed match does not copy `postal_city`. City-level rules for that address are `unknown` with the explanation that the legal city was not resolved. State-level rules may use the sample `state` column, which is an assessor fact, and the audit line records that the city match failed.
- **Rationale**: The spec forbids treating the mailing city as the jurisdiction. It also requires `unknown` rather than a guess. The state column is already a supplied fact.
- **Alternatives considered**: Dropping state rules whenever geocoding fails. Rejected because the state is present in the sample and state coverage does not need a city.

## 6. Coverage facts

- **Decision**: `coverage_conditions` is a JSON object, which the supplied schema allows. It carries a plain-language `summary` plus structured tests: geography, minimum and maximum units, a certificate-of-occupancy cutoff, and whether owner type is required. `year_built` is never compared to a certificate-of-occupancy cutoff. A missing fact, or a construction year equal to the cutoff year, yields `unknown` and names the fact. Owner type is always `unknown` because the sample has no owner names.
- **Rationale**: A prose-only condition cannot be tested the same way twice. The schema already permits an object, so the submission stays valid.
- **Alternatives considered**: Storing conditions only as strings and parsing them later. Rejected because the parse would be a second, hidden extraction. Treating `year_built` as the certificate date. Forbidden by the spec.

## 7. Status across dates

- **Decision**: `status` on a rule record is the status as of 2026-10-01. The lookup recomputes the result for another date from `effective_date` and from `status` when that status is `pending` or `failed`. A `failed` rule never applies. A `pending` rule stays `pending`. A rule with an effective date is `not_yet_effective` before that date and eligible to apply on and after that date. The effective date must appear in the quoted span; it is not typed in from the participant guide alone.
- **Rationale**: Tests T1 and T3 ask for two dates. The schema's `status` field is defined as of the default query date, so the date math has to live in the lookup.
- **Alternatives considered**: One frozen status for every date. Rejected because T1 and T3 would fail. Hard-coding the five test outcomes. Rejected because the same date rule has to work for a reviewer-chosen as-of date.

## 8. Identifiers for the five tests

- **Decision**: The rules named by `dev/change_tests.json` use those ids as `team_rule_id`: `CA-ALG-01`, `HOB-ALG-01`, `JC-ALG-01`, `NJ-ALG-01`, `MA-ALG-P1`, `MA-ALG-P2`, and `MA-RENT-P1`. Every other rule uses `r-` plus a zero-padded number.
- **Rationale**: The change tests already name the rules. Reusing those ids keeps `changes.json` tied to the catalog without a second crosswalk.
- **Alternatives considered**: Only `r-NNNN` ids plus a map. Rejected because the map can drift from the test file.

## 9. Supersession and conflicts

- **Decision**: `overrides` lists the other `team_rule_id` values, and `interaction` says whether this rule supersedes them or yields to them. When a stricter local rule applies, the broader rule is returned as `superseded` and is not dropped. Conflicting published dates, and possible preemption of the Jersey City and Hoboken bans by the New Jersey FAIR Act, set `conflict_flag` and do not choose a winner. A missing official dollar figure is stored as no `key_value`, with `conflict_flag` set, rather than as an invented number.
- **Rationale**: The spec requires both the local rule and the superseded state rule to appear, and it requires the known open questions to stay flagged.
- **Alternatives considered**: Omitting superseded rules. Rejected because `superseded` is a required result value. Picking the earlier of two published dates. Rejected because that hides the conflict.

## 10. Storage, tests, and the demo page

- **Decision**: No database. The starter pack stays read-only. Generated files live under `output/`: `rules.json`, `lookups.json`, `changes.json`, `geocodes.json`, `audit.jsonl`, and a one-page method note. Tests are pytest plus `jsonschema` for Draft 2020-12. Network calls are absent from the default test run; geocoding tests read a saved Census response. The person-facing view is one local page served by the Python standard library. It shows the as-of date and states that the output is not legal advice and not a compliance certification.
- **Rationale**: Five hundred addresses and under one hundred documents do not need a server or a database. The page is the interface the spec requires. The standard library avoids a web framework for a single review screen.
- **Alternatives considered**: PostgreSQL. Rejected as unused capacity. A React or Streamlit app. Rejected because the page only has to present finished JSON. Scraping ecode360, AmLegal, or other link-only hosts. Forbidden.

## 11. What this research did not reopen

Spanish wording, confidence scores, a jurisdiction outside the starter pack, and a separate audit screen stay out of scope. The audit log is in scope. The method note is a deliverable, not a product feature.
