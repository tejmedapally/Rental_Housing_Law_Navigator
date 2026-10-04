"""Write the one-page note that explains how the catalog and lookups are produced."""

from __future__ import annotations

import csv
from pathlib import Path

from navigator.corpus import repo_root
from navigator.errors import CommandError


def write_method_note(path: Path | None = None) -> Path:
    """Write output/method-note.md from the starter-pack manifest."""

    root = repo_root()
    target = path or (root / "output" / "method-note.md")
    manifest = root / "data_and_code_base" / "corpus" / "corpus_manifest.csv"
    if not manifest.is_file():
        raise CommandError(f"Corpus manifest not found: {manifest}")
    read_ids, skipped = _manifest_groups(manifest)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(_note(read_ids, skipped), encoding="utf-8")
    temporary.replace(target)
    return target


def _manifest_groups(manifest: Path) -> tuple[list[str], list[str]]:
    read_ids: list[str] = []
    skipped: list[str] = []
    with manifest.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            doc_id = (row.get("doc_id") or "").strip()
            status = (row.get("status") or "").strip()
            text_file = (row.get("text_file") or "").strip()
            if status == "link-only" or not text_file or doc_id == "D056":
                reason = "link-only" if status == "link-only" else "no captured text"
                skipped.append(f"{doc_id} ({reason})")
                continue
            read_ids.append(doc_id)
    return read_ids, skipped


def _note(read_ids: list[str], skipped: list[str]) -> str:
    read_list = ", ".join(read_ids)
    skipped_list = ", ".join(skipped)
    return f"""# Method note

This page describes how the navigator reads the starter pack. It is not legal advice and it is not a compliance certification.

## Documents read

The pipeline reads the captured text files listed in `data_and_code_base/corpus/corpus_manifest.csv` after dropping each file's SOURCE and RETRIEVED header. {len(read_ids)} documents were read: {read_list}.

These rows were not read and cannot support a quoted span: {skipped_list}. Link-only pages are not fetched. D056 has no text file because the capture was refused, so it is not read. The Massachusetts rent-control ballot question is link-only document D059, so no captured span supports MA-RENT-P1 and no Boston or Cambridge rent cap is reported from that question. Hoboken and Jersey City algorithmic-ban pages in the manifest are link-only, so those local bans are not given invented text.

## How a span is checked

A rule is kept only when `quoted_span` is at least 20 characters and is an exact slice of the captured text for its `source_doc_id`. Whitespace may be collapsed only to locate that slice. The value stored in `rules.json` is the slice from the file, not a rewritten sentence. If `effective_date` is set, that date must appear in the slice. A dollar amount written in `key_value` must also appear in the slice. The California screening-fee statute states a base amount that may be adjusted; the record does not add a 2026 dollar figure the slice does not contain.

## How a missing fact becomes unknown

Coverage is tested against the legal city and state from the Census geocode cache. The mailing city is not the legal city. When a rule does not cover the address, it is omitted.

When a coverage test needs a fact the sample does not contain, the lookup result is `unknown` and the explanation names the gap. A missing unit count is named as unit count. A certificate-of-occupancy cutoff with no construction year is named as certificate of occupancy. A construction year equal to the cutoff year is unknown, and that year is named. Year built is not treated as the certificate-of-occupancy date. An owner-type exception is unknown because the sample has no owner names. A city rule whose legal city could not be resolved is unknown for that reason.

The default as-of date is 2026-10-01. A failed measure is omitted. A pending bill stays pending. An enacted rule before its effective date is not yet effective.
"""
