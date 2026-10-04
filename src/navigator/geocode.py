"""Resolve sample addresses with the Census single-address geographies service."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from navigator.errors import CommandError
from navigator.models import JurisdictionStack, SampleAddress

CENSUS_ENDPOINT = "https://geocoding.geo.census.gov/geocoder/geographies/address"
BENCHMARK = "Public_AR_Current"
VINTAGE = "Current_Current"


def parse_census_match(
    address: SampleAddress,
    payload: dict,
    retrieved_at: str,
) -> JurisdictionStack:
    """Read legal state, county, and incorporated place. The mailing city is not the legal city."""

    matches = (payload.get("result") or {}).get("addressMatches") or []
    if not matches:
        return _unmatched(address, retrieved_at, payload)
    match = matches[0]
    geographies = match.get("geographies") or {}
    state = _state_code(geographies) or address.state
    county = _basename((geographies.get("Counties") or [None])[0])
    place = _basename((geographies.get("Incorporated Places") or [None])[0])
    if not place:
        return JurisdictionStack(
            address_id=address.address_id,
            match_status="unincorporated",
            legal_state=state,
            legal_county=county,
            legal_city=None,
            postal_city=address.postal_city,
            retrieved_at=retrieved_at,
            raw_match=match,
        )
    return JurisdictionStack(
        address_id=address.address_id,
        match_status="matched",
        legal_state=state,
        legal_county=county,
        legal_city=place,
        postal_city=address.postal_city,
        retrieved_at=retrieved_at,
        raw_match=match,
    )


def geocode_addresses(
    addresses: list[SampleAddress],
    cache_path: Path,
    refresh: bool = False,
    retrieved_at: str = "2026-10-01T00:00Z",
) -> dict[str, dict]:
    """Fill output/geocodes.json. Rows already in the cache are left in place unless refresh is set."""

    cached = _read_cache(cache_path)
    if _reparse_cached(cached):
        _write_cache(cache_path, cached)
    for address in addresses:
        if address.address_id in cached and not refresh:
            continue
        payload = _fetch_census(address)
        stack = parse_census_match(address, payload, retrieved_at)
        cached[address.address_id] = stack_to_dict(stack, address)
        _write_cache(cache_path, cached)
        print(f"{address.address_id} {stack.match_status} {stack.legal_city or stack.legal_state}", flush=True)
    return cached


def stack_to_dict(stack: JurisdictionStack, address: SampleAddress | None = None) -> dict:
    record = {
        "address_id": stack.address_id,
        "match_status": stack.match_status,
        "legal_state": stack.legal_state,
        "legal_county": stack.legal_county,
        "legal_city": stack.legal_city,
        "postal_city": stack.postal_city,
        "retrieved_at": stack.retrieved_at,
        "raw_match": stack.raw_match,
    }
    if address is not None:
        record["street_address"] = address.street_address
        record["zip"] = address.zip
    return record


def stack_from_dict(record: dict) -> JurisdictionStack:
    return JurisdictionStack(
        address_id=record["address_id"],
        match_status=record.get("match_status") or "unmatched",
        legal_state=record.get("legal_state") or "",
        legal_county=record.get("legal_county"),
        legal_city=record.get("legal_city"),
        postal_city=record.get("postal_city") or "",
        retrieved_at=record.get("retrieved_at") or "",
        raw_match=record.get("raw_match"),
    )


def run_geocode(argv: list[str]) -> int:
    from navigator.corpus import load_addresses, repo_root

    refresh = "--refresh" in argv
    root = repo_root()
    cache_path = root / "output" / "geocodes.json"
    geocode_addresses(load_addresses(root), cache_path, refresh=refresh)
    print(f"Wrote {cache_path}")
    return 0


def _fetch_census(address: SampleAddress) -> dict:
    query = urllib.parse.urlencode(
        {
            "street": address.street_address,
            "city": address.postal_city,
            "state": address.state,
            "zip": address.zip,
            "benchmark": BENCHMARK,
            "vintage": VINTAGE,
            "format": "json",
        }
    )
    request = urllib.request.Request(f"{CENSUS_ENDPOINT}?{query}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise CommandError(f"Census geocoder failed for {address.address_id}: {exc}") from exc


def _reparse_cached(cached: dict[str, dict]) -> bool:
    """Apply the current place-name parser to rows already saved from Census."""

    changed = False
    for address_id, record in cached.items():
        payload = _payload_from_raw(record.get("raw_match"))
        if payload is None:
            continue
        address = SampleAddress(
            address_id=address_id,
            street_address=str(record.get("street_address") or ""),
            postal_city=str(record.get("postal_city") or ""),
            state=str(record.get("legal_state") or ""),
            zip=str(record.get("zip") or ""),
            year_built=None,
            units=None,
            use_code="",
            use_description="",
            source_dataset="",
            retrieved_at=str(record.get("retrieved_at") or ""),
        )
        stack = parse_census_match(address, payload, address.retrieved_at)
        updated = stack_to_dict(stack, address)
        if updated.get("legal_city") != record.get("legal_city") or updated.get("legal_county") != record.get("legal_county"):
            record.clear()
            record.update(updated)
            changed = True
    return changed


def _payload_from_raw(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    if "geographies" in raw:
        return {"result": {"addressMatches": [raw]}}
    if isinstance(raw.get("result"), dict):
        return raw
    return None


def _read_cache(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload.get("geocodes") or {})


def _write_cache(path: Path, geocodes: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"geocodes": geocodes}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise CommandError(f"Could not replace the geocode cache: {path}") from None
            time.sleep(0.25 * (attempt + 1))


def _unmatched(address: SampleAddress, retrieved_at: str, payload: dict) -> JurisdictionStack:
    return JurisdictionStack(
        address_id=address.address_id,
        match_status="unmatched",
        legal_state=address.state,
        legal_county=None,
        legal_city=None,
        postal_city=address.postal_city,
        retrieved_at=retrieved_at,
        raw_match=payload,
    )


def _basename(record: dict | None) -> str | None:
    """Use the Census BASENAME. Strip a class suffix only from NAME, so Jersey City stays intact."""

    if not record:
        return None
    basename = str(record.get("BASENAME") or "").strip()
    if basename:
        return basename
    name = str(record.get("NAME") or "").strip()
    for suffix in (" city", " county"):
        if name.casefold().endswith(suffix):
            name = name[: -len(suffix)].strip()
            break
    return name or None


def _state_code(geographies: dict) -> str | None:
    states = geographies.get("States") or []
    if not states:
        return None
    code = states[0].get("STUSAB")
    return str(code).upper() if code else None
