"""Load the starter-pack corpus and sample addresses. Never fetches missing text."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from navigator.errors import CommandError
from navigator.models import SampleAddress

_SKIPPED_DOC_IDS = frozenset({"D056"})


@dataclass(frozen=True)
class SourceDocument:
    """One captured corpus document with its header removed."""

    doc_id: str
    jurisdictions: str
    url: str
    source_type: str
    retrieved_at: str
    text_file: str
    text: str


def repo_root() -> Path:
    """Return the repository root that contains the starter pack."""

    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        manifest = candidate / "data_and_code_base" / "corpus" / "corpus_manifest.csv"
        if manifest.is_file():
            return candidate
    raise CommandError("Could not find data_and_code_base/corpus/corpus_manifest.csv")


def load_documents(root: Path | None = None) -> list[SourceDocument]:
    """Return captured documents from the starter pack. Link-only rows and D056 are omitted."""

    base = root or repo_root()
    return load_corpus_directory(base / "data_and_code_base" / "corpus")


def load_corpus_directory(corpus_dir: Path) -> list[SourceDocument]:
    """Return captured documents in one corpus directory. Does not fetch missing files."""

    manifest_path = corpus_dir / "corpus_manifest.csv"
    documents: list[SourceDocument] = []
    with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            document = _document_from_row(corpus_dir, row)
            if document is not None:
                documents.append(document)
    return documents


def load_addresses(root: Path | None = None) -> list[SampleAddress]:
    """Return every sample address. Empty year and unit cells stay None."""

    base = root or repo_root()
    path = base / "data_and_code_base" / "data" / "sample_addresses.csv"
    addresses = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            addresses.append(
                SampleAddress(
                    address_id=row["address_id"].strip(),
                    street_address=row["street_address"].strip(),
                    postal_city=row["postal_city"].strip(),
                    state=row["state"].strip(),
                    zip=row["zip"].strip(),
                    year_built=_optional_int(row["year_built"]),
                    units=_optional_int(row["units"]),
                    use_code=row["use_code"].strip(),
                    use_description=row["use_description"].strip(),
                    source_dataset=row["source_dataset"].strip(),
                    retrieved_at=row["retrieved_at"].strip(),
                )
            )
    return addresses


def _document_from_row(corpus_dir: Path, row: dict[str, str]) -> SourceDocument | None:
    doc_id = (row.get("doc_id") or "").strip()
    status = (row.get("status") or "").strip()
    text_file = (row.get("text_file") or "").strip()
    if doc_id in _SKIPPED_DOC_IDS or status == "link-only" or not text_file:
        return None
    path = corpus_dir / text_file
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    return SourceDocument(
        doc_id=doc_id,
        jurisdictions=(row.get("jurisdictions") or "").strip(),
        url=(row.get("url") or "").strip(),
        source_type=(row.get("source_type") or "").strip(),
        retrieved_at=(row.get("retrieved_at") or "").strip(),
        text_file=text_file,
        text=strip_source_header(raw),
    )


def strip_source_header(raw: str) -> str:
    """Drop the leading SOURCE and RETRIEVED lines from a corpus text file."""

    lines = raw.splitlines()
    index = 0
    saw_header = False
    while index < len(lines):
        line = lines[index]
        if line.startswith("SOURCE:") or line.startswith("RETRIEVED:"):
            saw_header = True
            index += 1
            continue
        if saw_header and line.strip() == "":
            index += 1
            continue
        break
    return "\n".join(lines[index:])


def _optional_int(value: str) -> int | None:
    stripped = value.strip()
    if not stripped:
        return None
    return int(stripped)
