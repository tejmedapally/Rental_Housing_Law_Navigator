# Contract: Demo page

Served by `python -m navigator demo` at `http://127.0.0.1:8765/`.

The page reads `output/rules.json`, `output/lookups.json`, and `output/geocodes.json`. It does not call a model or the Census service.

## Always visible

- The words "Not legal advice" and "Not a compliance certification" in the page banner.
- The lookup `as_of` date.
- No text that suggests how to avoid a rule.

## Address review

- A control lists all 500 `address_id` values.
- Choosing an id shows the mailing address, the legal state, the legal county, the legal city, and each lookup row.
- Each row shows the rule title, `result`, `explanation`, citation, source document id, retrieval date, and the quoted span.
- A `conflict_flag` true row is visibly marked for human review.
- An empty list states that no supplied rule applies to that address on the as-of date.

## Change cases

- A second section lists T1 through T5 with the affected count, the conflict-flag count, and the notes from `output/changes.json`.

## Out of scope on this page

- Spanish text.
- A confidence control.
- Editing a rule.
- Addresses outside the sample.
