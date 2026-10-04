# Contract: Command line

Entry point: `.venv\Scripts\python.exe -m navigator` from the repository root.

The starter pack is an input. Commands write only under `output/` and append to `output/audit.jsonl`.

| Command | Reads | Writes | Success |
|---|---|---|---|
| `extract` | Corpus manifest and `corpus/text/` | `output/rules.json` | Verifier in `rule-record.md` passes. Exits 0 |
| `geocode` | `sample_addresses.csv` and the Census geographies service | `output/geocodes.json` | One row per sample address. Exits 0 |
| `lookup --as-of YYYY-MM-DD` | Rules, geocodes, sample | `output/lookups.json` when the date is 2026-10-01. Other dates print the same envelope and do not replace the default file | Envelope in `lookups.md`. Exits 0 |
| `changes` | Rules, geocodes, sample, `change_tests.json` | `output/changes.json` | Envelope in `changes.md`. Exits 0 |
| `validate` | The three output files and the text files | Nothing | Schema, span, 500-id, and T1–T5 checks pass. Exits 0 |
| `demo` | The three output files | Nothing | Serves the page in `demo-view.md` on `127.0.0.1` and prints the URL |

`extract` refuses to run a network fetch for any manifest row without a text file. `geocode` is the only command that calls the network, and only the Census geocoder. If `output/geocodes.json` already has all 500 ids, `geocode` leaves those rows in place unless `--refresh` is passed.

`extract` calls a model only when `NAVIGATOR_MODEL_BASE_URL` is set. Without it, `extract` still verifies any candidate file passed with `--candidates PATH` and writes the accepted records. A candidate that fails the verifier is reported and omitted, not rewritten to force a pass.

Shared failure behavior: a non-zero exit and a message on standard error. A failed command does not delete the previous `output/` file.
