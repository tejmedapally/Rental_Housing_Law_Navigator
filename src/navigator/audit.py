"""Append-only audit log. Existing output files are never truncated or deleted."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from navigator.corpus import repo_root

AUDIT_REASONS = frozenset(
    {
        "eligible",
        "outside_jurisdiction",
        "before_effective_date",
        "pending",
        "failed",
        "missing_units",
        "missing_year",
        "co_cutoff_year",
        "owner_type",
        "city_unresolved",
        "superseded_by",
        "conflict_review",
    }
)


@dataclass
class AuditRecord:
    """One replayable decision line."""

    address_id: str | None
    as_of: str
    team_rule_id: str
    result: str
    reason: str
    source_doc_id: str
    source_retrieved_at: str
    quoted_span: str

    def to_json(self) -> dict:
        if self.reason not in AUDIT_REASONS:
            raise ValueError(f"Unknown audit reason: {self.reason}")
        return {
            "address_id": self.address_id,
            "as_of": self.as_of,
            "team_rule_id": self.team_rule_id,
            "result": self.result,
            "reason": self.reason,
            "source_doc_id": self.source_doc_id,
            "source_retrieved_at": self.source_retrieved_at,
            "quoted_span_sha256": hashlib.sha256(self.quoted_span.encode("utf-8")).hexdigest(),
        }


def audit_path(root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / "output" / "audit.jsonl"


def append_audit(record: AuditRecord, path: Path | None = None) -> None:
    """Append one JSON object as a line. Does not rewrite earlier lines."""

    target = path or audit_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_json(), ensure_ascii=False)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
