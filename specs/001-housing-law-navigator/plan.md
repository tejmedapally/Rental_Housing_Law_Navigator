# Implementation Plan: Rental Housing Law Navigator

**Branch**: `001-housing-law-navigator` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-housing-law-navigator/spec.md`

## Summary

The navigator reads the supplied housing-law corpus, checks every quoted passage against the source file, resolves each of the 500 sample addresses to a Census incorporated place, and writes the three submission files. Lookup and the five change cases then run offline from those files. A local page shows one address at a time with the as-of date and a not-legal-advice banner.

Technical choices are recorded in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13.15 in `.venv`. The system `python` alias is not used.

**Primary Dependencies**: `jsonschema` for Draft 2020-12, `pytest` for the default test run. HTTP uses the standard library. A model is optional and only through `NAVIGATOR_MODEL_BASE_URL`.

**Storage**: JSON and JSONL files under `output/`. The starter pack is read-only. No database.

**Testing**: pytest. Schema validation, exact span checks, a 500-address lookup fixture, and T1–T5. The default test run does not use the network.

**Target Platform**: Local Windows workstation. The same commands run wherever the virtual environment exists. The demo page is a browser on `127.0.0.1`.

**Project Type**: Local command-line pipeline plus one review page.

**Performance Goals**: After geocodes and the catalog are cached, building all 500 lookups finishes in under 10 seconds. The demo opens a saved address without a model call.

**Constraints**: Public starter-pack text and the Census geocoder only. No fetches of link-only documents. Every accepted rule quotes a real source slice. Missing coverage facts stay `unknown`. Every page states that the output is not legal advice. Default as-of date is 2026-10-01.

**Scale/Scope**: 87 manifest rows, the captured text files, 500 addresses, six rule categories, three states, ten cities, five change cases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Plan result |
|---|---|---|
| I. Traceable Citations | A record is stored only when `quoted_span` is an exact slice of the cited text file, with URL and retrieval date | Pass. The verifier rejects everything else |
| II. Automated Extraction | The catalog is produced by reading corpus files. Hand-written prose is not the source of truth | Pass. Candidates come from the extractor or a candidate file, and both pass the same verifier |
| III. Unknown Over Guessing | Missing units, certificate of occupancy, cutoff year, and owner type return `unknown` | Pass. `year_built` is never compared to a certificate date. Owner type is always unknown |
| IV. Honest Legal Status | Status, result values, and conflict flags stay distinct across as-of dates | Pass. Stored status is as of 2026-10-01. Other dates are computed from `effective_date`. Conflicts are flagged |
| V. Public Data and Not Legal Advice | Starter pack plus Census only. The page carries the disclaimer | Pass. Link-only rows are not fetched. The demo banner is part of the page contract |

No gate failed. The Complexity Tracking section is empty.

Post-design re-check: the contracts require the span verifier, the Census incorporated-place cache, the `unknown` reasons, the T1–T5 sets, and the disclaimer banner. No new dependency reads private data or scrapes publisher sites. The post-design gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/001-housing-law-navigator/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rule-record.md
│   ├── lookups.md
│   ├── changes.md
│   ├── cli.md
│   └── demo-view.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
src/navigator/
├── __main__.py           # command dispatch
├── corpus.py             # manifest load; skip rows with no text
├── extract.py            # propose candidates and verify spans
├── geocode.py            # Census single-address geographies, then cache
├── coverage.py           # date gate, jurisdiction, missing facts, supersession
├── changes.py            # T1–T5
├── audit.py              # append JSONL
├── validate.py           # schema, spans, 500 ids, change sets
└── demo/
    └── index.html        # review page

tests/
├── fixtures/             # saved Census match and a tiny corpus slice
├── test_extract.py
├── test_coverage.py
├── test_changes.py
└── test_contracts.py

output/                   # generated, not part of the starter pack
data_and_code_base/       # read-only inputs
```

**Structure Decision**: One Python package under `src/navigator` with a standard-library demo page. The starter pack stays where it is. Generated submission files go to `output/` so a run cannot overwrite the corpus or the schemas.

## Complexity Tracking

No constitution violations require justification.
