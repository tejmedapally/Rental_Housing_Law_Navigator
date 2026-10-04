"""Command dispatcher for extract, geocode, lookup, changes, validate, and demo."""

from __future__ import annotations

import sys

from navigator.changes import run_changes
from navigator.coverage import run_lookup
from navigator.demo_server import run_demo
from navigator.errors import CommandError
from navigator.extract import run_extract
from navigator.geocode import run_geocode
from navigator.validate import run_validate

COMMANDS = ("extract", "geocode", "lookup", "changes", "validate", "demo")


def main(argv: list[str] | None = None) -> int:
    """Dispatch one command. Failures print to stderr and leave output/ alone."""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in COMMANDS:
        print(
            "usage: python -m navigator {extract|geocode|lookup|changes|validate|demo}",
            file=sys.stderr,
        )
        return 2
    try:
        if args[0] == "extract":
            return run_extract(args[1:])
        if args[0] == "geocode":
            return run_geocode(args[1:])
        if args[0] == "lookup":
            return run_lookup(args[1:])
        if args[0] == "changes":
            return run_changes(args[1:])
        if args[0] == "validate":
            return run_validate(args[1:])
        if args[0] == "demo":
            return run_demo(args[1:])
        _unimplemented(args[0])
    except CommandError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _unimplemented(command: str) -> None:
    raise CommandError(f"{command} is not implemented yet")


if __name__ == "__main__":
    sys.exit(main())
