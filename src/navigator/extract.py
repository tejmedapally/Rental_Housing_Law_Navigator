"""Read rule candidates, keep only quoted spans that exist in a captured file, and write the catalog."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from navigator.corpus import SourceDocument, load_corpus_directory, repo_root
from navigator.errors import CommandError
from navigator.models import CoverageConditions, Geography, RuleRecord

RESERVED_RULE_IDS = frozenset(
    {
        "CA-ALG-01",
        "HOB-ALG-01",
        "JC-ALG-01",
        "NJ-ALG-01",
        "MA-ALG-P1",
        "MA-ALG-P2",
        "MA-RENT-P1",
    }
)
_RULE_ID = re.compile(r"r-\d{4}$")
_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
_DOLLAR = re.compile(r"\$\d[\d,]*(?:\.\d+)?")
_LEVELS = frozenset({"state", "city"})
_CATEGORIES = frozenset(
    {
        "rent_increase_limits",
        "just_cause_eviction",
        "security_deposits",
        "application_screening_fees",
        "screening_restrictions",
        "algorithmic_rent_setting",
    }
)
_STATUSES = frozenset({"in_force", "not_yet_effective", "pending", "failed"})
# Captured bills named by the change tests. The first algorithmic rule from each file keeps that id.
_RESERVED_SOURCE = {
    ("D022", "algorithmic_rent_setting"): "CA-ALG-01",
    ("D045", "algorithmic_rent_setting"): "MA-ALG-P2",
    ("D046", "algorithmic_rent_setting"): "MA-ALG-P1",
    ("D069", "algorithmic_rent_setting"): "NJ-ALG-01",
}
_EXTRACTION_PROMPT = (
    "Extract housing rules from the document. Return JSON only, as "
    '{"rules": [...]}. Each object uses jurisdiction (a state code or '
    "'City, ST'), level ('state' or 'city'), category (one of "
    "rent_increase_limits, just_cause_eviction, security_deposits, "
    "application_screening_fees, screening_restrictions, algorithmic_rent_setting), "
    "status (one of in_force, not_yet_effective, pending, failed), title, "
    "requirement, citation, and quoted_span. quoted_span must be a contiguous "
    "copy of the document text, at least 20 characters, with the same words and "
    "punctuation. Do not paraphrase or insert ellipses. Omit a rule when you "
    "cannot copy such a span. Omit team_rule_id. When coverage_conditions is "
    "present, it is an object with summary and geography {level, name}."
)


def verify_candidates(
    candidates: list[dict],
    documents: dict[str, SourceDocument],
) -> tuple[list[RuleRecord], list[str]]:
    """Accept candidates whose quotes are real slices. Rejections are omitted, not rewritten."""

    accepted: list[RuleRecord] = []
    rejected: list[str] = []
    used_ids: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        label = str(candidate.get("team_rule_id") or f"candidate {index}")
        try:
            rule = _verify_one(candidate, documents, used_ids)
        except ValueError as exc:
            rejected.append(f"{label}: {exc}")
            continue
        used_ids.add(rule.team_rule_id)
        accepted.append(rule)
    return accepted, rejected


def _stored_rule_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    rules = payload.get("rules") if isinstance(payload, dict) else None
    return len(rules) if isinstance(rules, list) else 0


def apply_reserved_ids(rules: list[RuleRecord]) -> None:
    """Give the change-test ids to the captured bills those tests name."""

    claimed: set[str] = set()
    for rule in rules:
        reserved = _RESERVED_SOURCE.get((rule.source_doc_id, rule.category))
        if reserved is None or reserved in claimed:
            continue
        claimed.add(reserved)
        rule.team_rule_id = reserved


def write_rules(rules: list[RuleRecord], path: Path) -> None:
    """Write the catalog. The previous file is replaced only after the new text is complete."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rules": [rule_to_dict(rule) for rule in rules]}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def rule_to_dict(rule: RuleRecord) -> dict:
    coverage = None
    if rule.coverage_conditions is not None:
        item = rule.coverage_conditions
        coverage = {
            "summary": item.summary,
            "geography": {"level": item.geography.level, "name": item.geography.name},
            "min_units": item.min_units,
            "max_units": item.max_units,
            "certificate_of_occupancy_on_or_before": item.certificate_of_occupancy_on_or_before,
            "requires_owner_type": item.requires_owner_type,
        }
    return {
        "team_rule_id": rule.team_rule_id,
        "jurisdiction": rule.jurisdiction,
        "level": rule.level,
        "category": rule.category,
        "status": rule.status,
        "title": rule.title,
        "requirement": rule.requirement,
        "key_value": rule.key_value,
        "coverage_conditions": coverage,
        "exemptions": rule.exemptions,
        "overrides": list(rule.overrides),
        "interaction": rule.interaction,
        "effective_date": rule.effective_date,
        "citation": rule.citation,
        "source_doc_id": rule.source_doc_id,
        "source_url": rule.source_url,
        "quoted_span": rule.quoted_span,
        "confidence": rule.confidence,
        "conflict_flag": rule.conflict_flag,
        "conflict_note": rule.conflict_note,
    }


def load_candidate_file(path: Path) -> list[dict]:
    if not path.is_file():
        raise CommandError(f"Candidates file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rules"), list):
        return payload["rules"]
    raise CommandError('Candidates file must be a list or {"rules": [...]}')


def bind_source(candidates: list[dict], document: SourceDocument) -> list[dict]:
    """Record which captured file a proposal came from. The model often omits that field."""

    bound: list[dict] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        item = dict(candidate)
        item["source_doc_id"] = document.doc_id
        item["source_url"] = document.url
        bound.append(item)
    return bound


def propose_rules(document: SourceDocument) -> list[dict]:
    """Ask a model for rule records. Not used when --candidates is set."""

    base_url = os.environ.get("NAVIGATOR_MODEL_BASE_URL", "").strip()
    if base_url:
        return _propose_compatible(document, base_url)
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return _propose_anthropic(document)
    raise CommandError("Set ANTHROPIC_API_KEY or NAVIGATOR_MODEL_BASE_URL, or pass --candidates")


def _propose_compatible(document: SourceDocument, base_url: str) -> list[dict]:
    model = os.environ.get("NAVIGATOR_MODEL_NAME", "").strip()
    if not model:
        raise CommandError("Set NAVIGATOR_MODEL_NAME")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(_chat_body(document, model)).encode("utf-8"),
        headers=_chat_headers(),
        method="POST",
    )
    payload = _read_model_response(document, request)
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise CommandError(f"Model response for {document.doc_id} did not contain text")
    return parse_model_rules(content)


def _propose_anthropic(document: SourceDocument) -> list[dict]:
    model = os.environ.get("NAVIGATOR_MODEL_NAME", "").strip() or "claude-sonnet-5"
    key = os.environ["ANTHROPIC_API_KEY"].strip()
    body = _chat_body(document, model)
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(
            {
                "model": model,
                "max_tokens": 16000,
                "system": body["messages"][0]["content"],
                "messages": [body["messages"][1]],
            }
        ).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    payload = _read_model_response(document, request)
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        raise CommandError(f"Model response for {document.doc_id} did not contain text")
    content = "".join(block.get("text", "") for block in blocks if isinstance(block, dict))
    if not content.strip():
        raise CommandError(f"Model response for {document.doc_id} did not contain text")
    return parse_model_rules(content)


def _read_model_response(document: SourceDocument, request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise CommandError(f"Model request failed for {document.doc_id}: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise CommandError(f"Model request failed for {document.doc_id}: {exc}") from exc


def parse_model_rules(content: str) -> list[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rules", [])
    if not isinstance(payload, list):
        raise CommandError("Model response did not contain a rules list")
    return payload


def run_extract(argv: list[str]) -> int:
    """Verify candidates or model proposals and write output/rules.json."""

    options = _parse_extract_args(argv)
    corpus_dir = options["corpus"] or (repo_root() / "data_and_code_base" / "corpus")
    output = options["output"] or (repo_root() / "output" / "rules.json")
    documents = {item.doc_id: item for item in load_corpus_directory(corpus_dir)}
    if options["candidates"] is not None:
        raw_rules = load_candidate_file(options["candidates"])
    else:
        raw_rules = []
        proposals = output.parent / "model-proposals.jsonl"
        proposals.write_text("", encoding="utf-8")
        for document in documents.values():
            try:
                proposed = bind_source(propose_rules(document), document)
            except (CommandError, json.JSONDecodeError, TimeoutError, OSError) as exc:
                print(f"{document.doc_id}: {exc}", file=sys.stderr, flush=True)
                with proposals.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"doc_id": document.doc_id, "error": str(exc)}, ensure_ascii=False) + "\n")
                continue
            print(f"{document.doc_id}: {len(proposed)} candidates", flush=True)
            with proposals.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"doc_id": document.doc_id, "rules": proposed}, ensure_ascii=False) + "\n")
            raw_rules.extend(proposed)
    accepted, rejected = verify_candidates(raw_rules, documents)
    for message in rejected:
        print(message, file=sys.stderr)
    if not accepted and _stored_rule_count(output):
        print(f"Kept {output}: no candidate passed the span check", file=sys.stderr)
        return 1
    apply_reserved_ids(accepted)
    write_rules(accepted, output)
    return 0 if accepted else 1


def exact_slice(haystack: str, needle: str) -> str | None:
    """Return the file slice for needle, collapsing whitespace only while searching."""

    if needle in haystack:
        return needle
    collapsed_haystack, index_map = _collapse(haystack)
    collapsed_needle, _index_map = _collapse(needle)
    collapsed_needle = collapsed_needle.strip()
    if not collapsed_needle:
        return None
    start = collapsed_haystack.find(collapsed_needle)
    if start < 0:
        return None
    original_start = index_map[start]
    original_end = index_map[start + len(collapsed_needle) - 1] + 1
    return haystack[original_start:original_end]


def _verify_one(candidate: dict, documents: dict[str, SourceDocument], used_ids: set[str]) -> RuleRecord:
    doc_id = str(candidate.get("source_doc_id") or "").strip()
    document = documents.get(doc_id)
    if document is None:
        raise ValueError(f"source_doc_id {doc_id or '(missing)'} has no captured text")
    source_url = str(candidate.get("source_url") or "").strip()
    if source_url != document.url:
        raise ValueError("source_url does not match the manifest")
    quoted = candidate.get("quoted_span")
    if not isinstance(quoted, str) or len(quoted) < 20:
        raise ValueError("quoted_span must be at least 20 characters")
    stored = exact_slice(document.text, quoted)
    if stored is None or len(stored) < 20:
        raise ValueError("quoted_span is not a slice of the source text")
    effective_date = candidate.get("effective_date")
    if effective_date is not None:
        effective_date = str(effective_date)
        if not _DATE.match(effective_date):
            raise ValueError("effective_date is not a date")
        if effective_date not in stored:
            raise ValueError("effective_date does not occur in quoted_span")
    level = candidate.get("level")
    category = candidate.get("category")
    status = candidate.get("status")
    if level not in _LEVELS or category not in _CATEGORIES or status not in _STATUSES:
        raise ValueError("level, category, or status is outside the allowed values")
    coverage = _coverage(candidate.get("coverage_conditions"))
    key_value = candidate.get("key_value")
    if key_value is not None:
        key_value = str(key_value)
        for amount in _DOLLAR.findall(key_value):
            if amount not in stored:
                raise ValueError("key_value states a dollar amount that is not in quoted_span")
    team_rule_id = _rule_id(candidate.get("team_rule_id"), used_ids)
    for required in ("jurisdiction", "title", "requirement", "citation"):
        if not str(candidate.get(required) or "").strip():
            raise ValueError(f"{required} is required")
    return RuleRecord(
        team_rule_id=team_rule_id,
        jurisdiction=str(candidate["jurisdiction"]).strip(),
        level=level,
        category=category,
        status=status,
        title=str(candidate["title"]).strip(),
        requirement=str(candidate["requirement"]).strip(),
        citation=str(candidate["citation"]).strip(),
        source_url=source_url,
        quoted_span=stored,
        key_value=key_value,
        coverage_conditions=coverage,
        exemptions=candidate.get("exemptions"),
        overrides=list(candidate.get("overrides") or []),
        interaction=candidate.get("interaction"),
        effective_date=effective_date,
        source_doc_id=doc_id,
        confidence=candidate.get("confidence"),
        conflict_flag=bool(candidate.get("conflict_flag", False)),
        conflict_note=candidate.get("conflict_note"),
    )


def _rule_id(value: object, used_ids: set[str]) -> str:
    if value is None or str(value).strip() == "":
        number = 1
        while True:
            candidate = f"r-{number:04d}"
            if candidate not in used_ids:
                return candidate
            number += 1
    rule_id = str(value).strip()
    if rule_id not in RESERVED_RULE_IDS and _RULE_ID.match(rule_id) is None:
        raise ValueError("team_rule_id must be a reserved test id or r-NNNN")
    if rule_id in used_ids:
        raise ValueError("team_rule_id is duplicated")
    return rule_id


def _coverage(value: object) -> CoverageConditions | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("coverage_conditions must be an object")
    geography = value.get("geography")
    if not isinstance(geography, dict) or not value.get("summary") or not geography.get("level") or not geography.get("name"):
        raise ValueError("coverage_conditions is missing summary or geography")
    return CoverageConditions(
        summary=str(value["summary"]),
        geography=Geography(level=str(geography["level"]), name=str(geography["name"])),
        min_units=value.get("min_units"),
        max_units=value.get("max_units"),
        certificate_of_occupancy_on_or_before=value.get("certificate_of_occupancy_on_or_before"),
        requires_owner_type=bool(value.get("requires_owner_type", False)),
    )


def _collapse(text: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    index_map: list[int] = []
    previous_space = False
    for index, character in enumerate(text):
        if character.isspace():
            if characters and not previous_space:
                characters.append(" ")
                index_map.append(index)
            previous_space = True
            continue
        characters.append(character)
        index_map.append(index)
        previous_space = False
    return "".join(characters), index_map


def _chat_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("NAVIGATOR_MODEL_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _chat_body(document: SourceDocument, model: str) -> dict:
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    _EXTRACTION_PROMPT
                ),
            },
            {
                "role": "user",
                "content": f"doc_id: {document.doc_id}\nurl: {document.url}\n\n{document.text}",
            },
        ],
    }


def _parse_extract_args(argv: list[str]) -> dict:
    options: dict[str, Path | None] = {"candidates": None, "corpus": None, "output": None}
    index = 0
    flags = {"--candidates": "candidates", "--corpus": "corpus", "--output": "output"}
    while index < len(argv):
        flag = argv[index]
        if flag not in flags or index + 1 >= len(argv):
            raise CommandError(
                "usage: python -m navigator extract [--candidates PATH] [--corpus DIR] [--output PATH]"
            )
        options[flags[flag]] = Path(argv[index + 1])
        index += 2
    return options
