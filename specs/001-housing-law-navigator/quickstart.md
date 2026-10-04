# Quickstart: Rental Housing Law Navigator

Validation guide for the pipeline in [plan.md](plan.md). Contracts live in [contracts/](contracts/). The field definitions live in [data-model.md](data-model.md).

## Prerequisites

- Repository root as the working directory.
- Python 3.13 from `.venv` (`Python 3.13.15`). Do not use the system `python` alias.
- The starter pack at `data_and_code_base/` left unchanged.
- Network access only for the first `geocode` run. Later runs and `pytest` stay offline.
- `NAVIGATOR_MODEL_BASE_URL` set only when producing a fresh candidate catalog. Lookup and validation do not need it.

Install the test dependency into the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip install jsonschema pytest
```

## Produce the submission

```powershell
.\.venv\Scripts\python.exe -m navigator extract
.\.venv\Scripts\python.exe -m navigator geocode
.\.venv\Scripts\python.exe -m navigator lookup --as-of 2026-10-01
.\.venv\Scripts\python.exe -m navigator changes
.\.venv\Scripts\python.exe -m navigator validate
```

`extract` sends each captured file to the model, then keeps a rule only when its quote is a slice of that file. Set `ANTHROPIC_API_KEY` in the shell, or set `NAVIGATOR_MODEL_BASE_URL` for an OpenAI-compatible endpoint. The key is not stored in the project. `--candidates PATH` reruns the verifier on a correction file. It does not author rules.

Expected files:

| File | Expected |
|---|---|
| `output/rules.json` | Schema-valid catalog. Quoted spans match the text files. Santa Ana is present. Link-only docs are absent |
| `output/geocodes.json` | 500 rows. `legal_city` comes from Incorporated Place |
| `output/lookups.json` | `as_of` 2026-10-01 and all 500 address ids |
| `output/changes.json` | T1–T5 sets in [contracts/changes.md](contracts/changes.md) |
| `output/audit.jsonl` | One line per lookup decision |
| `output/method-note.md` | One page: what was read, how a span is checked, how a missing fact becomes `unknown` |

`validate` exits 0 only when those checks pass.

## Check the date and boundary cases

```powershell
.\.venv\Scripts\python.exe -m navigator lookup --as-of 2025-12-31 --rule CA-ALG-01
.\.venv\Scripts\python.exe -m navigator lookup --as-of 2026-01-02 --rule CA-ALG-01
.\.venv\Scripts\python.exe -m navigator lookup --as-of 2027-07-02 --rule NJ-ALG-01
```

Expected:

- 2025-12-31: `CA-ALG-01` is `not_yet_effective` for every California address.
- 2026-01-02: `CA-ALG-01` is `applies` for every California address.
- 2027-07-02: `NJ-ALG-01` is `applies` for every New Jersey address, and Jersey City and Hoboken rows are `conflict_flag` true.
- Hoboken's ban is only on Hoboken legal cities. Jersey City's ban is only on Jersey City. Newark has neither.
- Massachusetts S.2983 and H.5222 are `pending`. The rent-control question contributes an empty T5 affected set.

These date-specific lookups print JSON. They do not overwrite `output/lookups.json`.

## Open the demo

```powershell
.\.venv\Scripts\python.exe -m navigator demo
```

Open `http://127.0.0.1:8765/`. Confirm the banner says the page is not legal advice and not a compliance certification, the as-of date is 2026-10-01, and one sample address shows its legal city rather than only its mailing city.

## Automated check

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The default run does not call the Census service or a model. It uses the saved geocode cache and the verified catalog.
