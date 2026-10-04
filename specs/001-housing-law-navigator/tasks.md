# Tasks: Rental Housing Law Navigator

**Input**: Design documents from `/specs/001-housing-law-navigator/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. plan.md and quickstart.md require pytest for the constitution gates. Write each story's tests first and confirm they fail before that story's implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/navigator/`, `tests/` at repository root
- Generated files go to `output/`. `data_and_code_base/` stays read-only
- Use `.venv\Scripts\python.exe`. Do not use the system `python` alias

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create `src/navigator/`, `src/navigator/demo/`, `tests/fixtures/`, and `output/.gitkeep` as specified in `specs/001-housing-law-navigator/plan.md`
- [x] T002 [P] Add `pyproject.toml` with Python 3.13, dependencies `jsonschema` and `pytest`, and a `src` package layout so `.venv\Scripts\python.exe -m navigator` resolves
- [x] T003 [P] Add the package marker `src/navigator/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Implement corpus and sample loading in `src/navigator/corpus.py`: read `data_and_code_base/corpus/corpus_manifest.csv` and `data_and_code_base/data/sample_addresses.csv`, return header-stripped text only for rows with a text file, and skip link-only rows and `D056`
- [x] T005 [P] Implement the JSONL audit writer in `src/navigator/audit.py` for `output/audit.jsonl` using the audit fields in `specs/001-housing-law-navigator/data-model.md`
- [x] T006 [P] Implement shared records in `src/navigator/models.py` for a rule, a sample address, a jurisdiction stack, and a lookup result, including the coverage object from `specs/001-housing-law-navigator/data-model.md`
- [x] T007 [P] Implement `CommandError` in `src/navigator/errors.py` so failures print to standard error and do not delete an existing `output/` file
- [x] T008 Implement the command dispatcher in `src/navigator/__main__.py` with `extract`, `geocode`, `lookup`, `changes`, `validate`, and `demo` stubs that raise `CommandError` until a later task fills them in

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Cited rule catalog (Priority: P1) 🎯 MVP

**Goal**: Produce a schema-valid catalog in which every rule quotes a real slice of a captured corpus file. Santa Ana rules are included. Link-only sources contribute nothing.

**Independent Test**: Run `.venv\Scripts\python.exe -m pytest tests/test_extract.py`. A catalog built from `tests/fixtures/corpus/` accepts only exact spans of at least 20 characters, rejects a link-only document, and stores status as `in_force`, `not_yet_effective`, `pending`, or `failed`.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Add a tiny captured document and a link-only manifest row under `tests/fixtures/corpus/`
- [x] T010 [P] [US1] Write failing verifier tests in `tests/test_extract.py` for the span, link-only, effective-date, and duplicate-id rules in `specs/001-housing-law-navigator/contracts/rule-record.md`

### Implementation for User Story 1

- [x] T011 [US1] Implement the quoted-span verifier in `src/navigator/extract.py`: collapse whitespace only to locate the slice, store the exact file slice, reject spans shorter than 20 characters, and reject any `source_doc_id` without a text file
- [x] T012 [US1] Implement candidate loading via `--candidates` and the optional OpenAI-compatible proposer behind `NAVIGATOR_MODEL_BASE_URL` in `src/navigator/extract.py`, using the standard-library HTTP client
- [x] T013 [US1] Write accepted records to `output/rules.json` from `src/navigator/extract.py`, reserving `CA-ALG-01`, `HOB-ALG-01`, `JC-ALG-01`, `NJ-ALG-01`, `MA-ALG-P1`, `MA-ALG-P2`, and `MA-RENT-P1`, and assigning `r-NNNN` to every other rule
- [x] T014 [US1] Wire `extract` in `src/navigator/__main__.py` so it never fetches a manifest row that has no text file and so a rejected candidate is omitted rather than rewritten
- [x] T015 [US1] Add catalog-only checks in `src/navigator/validate.py` for schema validity, a Santa Ana city rule, no link-only `doc_id`, `MA-RENT-P1` status `failed`, and pending status on `MA-ALG-P1` and `MA-ALG-P2`

**Checkpoint**: User Story 1 is testable from the fixture corpus with no address sample

---

## Phase 4: User Story 2 - Address answer on a date (Priority: P1)

**Goal**: For a sample address and a date, return applicable rules with a plain-language explanation, a citation, and `unknown` when a required fact is missing. The review page shows the as-of date and states that the output is not legal advice.

**Independent Test**: Run `.venv\Scripts\python.exe -m pytest tests/test_coverage.py`. A fixture address mailed as a neighborhood resolves to the Census incorporated place. A missing unit count, a certificate-of-occupancy cutoff year, and any owner-type test return `unknown` and name the missing fact. A stricter local rule leaves the broader rule as `superseded`.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T016 [P] [US2] Add a saved Census geographies match, including an Incorporated Place, in `tests/fixtures/census_match.json`
- [x] T017 [P] [US2] Write failing lookup tests in `tests/test_coverage.py` for jurisdiction, missing facts, cutoff year, owner type, supersession, and the 2026-10-01 envelope in `specs/001-housing-law-navigator/contracts/lookups.md`
- [x] T018 [P] [US2] Build the address review section of `src/navigator/demo/index.html` with the not-legal-advice banner, the as-of date, the legal city, and the quoted span from `specs/001-housing-law-navigator/contracts/demo-view.md`

### Implementation for User Story 2

- [x] T019 [US2] Implement the Census single-address client and `output/geocodes.json` cache in `src/navigator/geocode.py` using benchmark `Public_AR_Current` and vintage `Current_Current`, and skip rows already cached unless `--refresh` is passed
- [x] T020 [US2] Implement the date gate, legal-city match, missing-fact `unknown` results, and supersession in `src/navigator/coverage.py` without comparing `year_built` to a certificate-of-occupancy date
- [x] T021 [US2] Wire `lookup --as-of` in `src/navigator/__main__.py` so 2026-10-01 writes `output/lookups.json` for all 500 sample ids, other dates only print JSON, and `src/navigator/coverage.py` appends one audit line per decision through `src/navigator/audit.py`
- [x] T022 [US2] Serve `src/navigator/demo/index.html` on `127.0.0.1:8765` from the `demo` command in `src/navigator/__main__.py`

**Checkpoint**: User Stories 1 and 2 both work. Story 2's tests use fixture rules and do not require a live model or the Census service

---

## Phase 5: User Story 3 - Supplied change cases (Priority: P2)

**Goal**: Report which sample addresses each of T1 through T5 affects, which addresses need a conflict review, and a short note.

**Independent Test**: Run `.venv\Scripts\python.exe -m pytest tests/test_changes.py`. T1 flips `CA-ALG-01` between 2025-12-31 and 2026-01-02 for California addresses. T2 keeps Hoboken and Jersey City bans inside those legal cities and out of Newark. T3 flags Jersey City and Hoboken. T4 lists Massachusetts addresses as pending impact. T5 has an empty affected set.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T023 [US3] Write failing change-set tests in `tests/test_changes.py` for the expected id sets in `specs/001-housing-law-navigator/contracts/changes.md` using fixture geocodes rather than the live Census service

### Implementation for User Story 3

- [x] T024 [US3] Implement T1–T5 in `src/navigator/changes.py` from `data_and_code_base/dev/change_tests.json`, `output/geocodes.json`, and the catalog, with sorted unique address ids
- [x] T025 [US3] Wire `changes` in `src/navigator/__main__.py` to write `output/changes.json` with notes for the Hoboken/Jersey City boundary, the pending Massachusetts bills, and the failed rent-control question
- [x] T026 [US3] Add the T1–T5 section to `src/navigator/demo/index.html` showing affected counts, conflict-flag counts, and notes from `output/changes.json`

**Checkpoint**: All three user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T027 Complete `validate` in `src/navigator/validate.py` so it checks rule spans, all 500 lookup ids, Santa Ana absent from lookups, `MA-RENT-P1` never `applies`, and the T1–T5 sets, then exits 0 only when every check passes
- [x] T028 [P] Write `output/method-note.md` from `src/navigator/method_note.py` describing which documents were read, how a span is checked, and how a missing fact becomes `unknown`
- [x] T029 [P] Add cross-file invariant tests in `tests/test_contracts.py` for the envelopes in `specs/001-housing-law-navigator/contracts/`
- [x] T030 Run the command sequence in `specs/001-housing-law-navigator/quickstart.md` and fix any failure in `src/navigator/` until `.venv\Scripts\python.exe -m navigator validate` exits 0

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Uses a fixture catalog in tests. The full `output/lookups.json` needs the User Story 1 catalog and the geocode cache
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses fixture geocodes in tests. The full `output/changes.json` needs legal cities from User Story 2 and rule ids from User Story 1

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Verifier and models before commands that write `output/`
- Story complete before moving to the next priority when working alone

### Parallel Opportunities

- T002 and T003 can run in parallel after T001
- T004, T005, T006, and T007 can run in parallel; T008 waits for them
- Once Foundational completes, User Story 1 and User Story 2 can start in parallel
- T009 and T010 can run in parallel
- T016, T017, and T018 can run in parallel
- T028 and T029 can run in parallel after T027's contract checks exist; T030 is last

---

## Parallel Example: User Story 1

```bash
Task: "Add a tiny captured document and a link-only manifest row under tests/fixtures/corpus/"
Task: "Write failing verifier tests in tests/test_extract.py for the span, link-only, effective-date, and duplicate-id rules in specs/001-housing-law-navigator/contracts/rule-record.md"
```

## Parallel Example: User Story 2

```bash
Task: "Add a saved Census geographies match, including an Incorporated Place, in tests/fixtures/census_match.json"
Task: "Write failing lookup tests in tests/test_coverage.py for jurisdiction, missing facts, cutoff year, owner type, supersession, and the 2026-10-01 envelope in specs/001-housing-law-navigator/contracts/lookups.md"
Task: "Build the address review section of src/navigator/demo/index.html with the not-legal-advice banner, the as-of date, the legal city, and the quoted span from specs/001-housing-law-navigator/contracts/demo-view.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `.venv\Scripts\python.exe -m pytest tests/test_extract.py`
5. Demo the catalog and the span check before geocoding

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Cited catalog is the MVP
3. Add User Story 2 → Address answers and the review page
4. Add User Story 3 → T1–T5 change report
5. Polish → `validate` exits 0 and the method note is written
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3 against fixture geocodes
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
