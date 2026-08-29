"""Stable API-version metadata."""

from .compat import StrEnum

RESOURCE_PROVIDER_API_VERSION = 1


class ReaderBackend(StrEnum):
    """Relation backends that can consume a native provider request."""

    POLARS = "polars"
    NARWHALS = "narwhals"
    IBIS = "ibis"


__all__ = ["RESOURCE_PROVIDER_API_VERSION", "ReaderBackend"]
