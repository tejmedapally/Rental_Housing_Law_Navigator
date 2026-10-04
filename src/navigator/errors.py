"""Command failures that leave output files in place."""


class CommandError(Exception):
    """A navigator command failed.

    Callers print the message to standard error and exit non-zero.
    They do not delete anything under output/.
    """
