# Method note

This page describes how the navigator reads the starter pack. It is not legal advice and it is not a compliance certification.

## Documents read

The pipeline reads the captured text files listed in `data_and_code_base/corpus/corpus_manifest.csv` after dropping each file's SOURCE and RETRIEVED header. 54 documents were read: D001, D003, D004, D005, D006, D007, D008, D009, D010, D011, D012, D013, D014, D016, D022, D023, D024, D025, D026, D027, D029, D031, D036, D039, D040, D041, D042, D043, D045, D046, D047, D048, D049, D050, D051, D052, D053, D057, D058, D065, D066, D067, D068, D069, D073, D076, D078, D079, D080, D081, D082, D083, D084, D085.

These rows were not read and cannot support a quoted span: D002 (link-only), D015 (link-only), D017 (link-only), D018 (link-only), D019 (link-only), D020 (link-only), D021 (link-only), D028 (link-only), D030 (link-only), D032 (link-only), D033 (link-only), D034 (link-only), D035 (link-only), D037 (link-only), D038 (link-only), D044 (link-only), D054 (link-only), D055 (link-only), D056 (no captured text), D059 (link-only), D060 (link-only), D061 (link-only), D062 (link-only), D063 (link-only), D064 (link-only), D070 (link-only), D071 (link-only), D072 (link-only), D074 (link-only), D075 (link-only), D077 (link-only), D086 (link-only), D087 (link-only). Link-only pages are not fetched. D056 has no text file because the capture was refused, so it is not read. The Massachusetts rent-control ballot question is link-only document D059, so no captured span supports MA-RENT-P1 and no Boston or Cambridge rent cap is reported from that question. Hoboken and Jersey City algorithmic-ban pages in the manifest are link-only, so those local bans are not given invented text.

## How a span is checked

A rule is kept only when `quoted_span` is at least 20 characters and is an exact slice of the captured text for its `source_doc_id`. Whitespace may be collapsed only to locate that slice. The value stored in `rules.json` is the slice from the file, not a rewritten sentence. If `effective_date` is set, that date must appear in the slice. A dollar amount written in `key_value` must also appear in the slice. The California screening-fee statute states a base amount that may be adjusted; the record does not add a 2026 dollar figure the slice does not contain.

## How a missing fact becomes unknown

Coverage is tested against the legal city and state from the Census geocode cache. The mailing city is not the legal city. When a rule does not cover the address, it is omitted.

When a coverage test needs a fact the sample does not contain, the lookup result is `unknown` and the explanation names the gap. A missing unit count is named as unit count. A certificate-of-occupancy cutoff with no construction year is named as certificate of occupancy. A construction year equal to the cutoff year is unknown, and that year is named. Year built is not treated as the certificate-of-occupancy date. An owner-type exception is unknown because the sample has no owner names. A city rule whose legal city could not be resolved is unknown for that reason.

The default as-of date is 2026-10-01. A failed measure is omitted. A pending bill stays pending. An enacted rule before its effective date is not yet effective.
