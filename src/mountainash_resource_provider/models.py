"""Immutable request, plan, and result values for resource providers."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa

from .compat import StrEnum
from .frozen import FrozenMap


class DialectFieldDisposition(StrEnum):
    """How a provider handles one declared dialect field."""

    CONSUMED = "consumed"
    INAPPLICABLE = "inapplicable"
    DEFERRED = "deferred"


class StructuredRowShape(StrEnum):
    """The data-dependent shape of a structured resource."""

    OBJECT = "object"
    ARRAY = "array"
    EMPTY = "empty"


DEFERRED_CONTEXT_KEYS = frozenset({"structured_row_shape"})


@dataclass(frozen=True, init=False)
class ProviderFormatDescriptor:
    """A provider's immutable format capability declaration."""

    canonical_format: str
    aliases: frozenset[str]
    suffixes: frozenset[str]
    mediatypes: frozenset[str]
    locator_prefixes: frozenset[str]
    dialect_family: str | None
    provider_format_key: str

    def __init__(
        self,
        canonical_format: str,
        aliases: Collection[str],
        suffixes: Collection[str],
        mediatypes: Collection[str],
        locator_prefixes: Collection[str],
        dialect_family: str | None,
        provider_format_key: str,
    ) -> None:
        from .formats import (
            normalize_format_name,
            normalize_locator_prefix,
            normalize_mediatype,
            normalize_suffix,
        )

        object.__setattr__(self, "canonical_format", normalize_format_name(canonical_format))
        object.__setattr__(
            self,
            "aliases",
            _normalize_strings(aliases, "aliases", normalize_format_name),
        )
        object.__setattr__(
            self,
            "suffixes",
            _normalize_strings(suffixes, "suffixes", normalize_suffix),
        )
        object.__setattr__(
            self,
            "mediatypes",
            _normalize_strings(
                mediatypes,
                "mediatypes",
                lambda value: normalize_mediatype(value, published=True),
            ),
        )
        object.__setattr__(
            self,
            "locator_prefixes",
            _normalize_strings(locator_prefixes, "locator_prefixes", normalize_locator_prefix),
        )
        object.__setattr__(self, "dialect_family", dialect_family)
        object.__setattr__(self, "provider_format_key", normalize_format_name(provider_format_key))


@dataclass(frozen=True)
class DetectedResourceFormat:
    """The physical format selected before provider planning."""

    canonical_format: str
    dialect_family: str | None
    provider_format_key: str
    detection_source: str


@dataclass(frozen=True, init=False)
class ResourceRequest:
    """The owned, provider-neutral operational request."""

    name: str
    locator: str | tuple[str, ...] = field(repr=False)
    detected_format: DetectedResourceFormat
    encoding: str | None
    dialect: FrozenMap
    dialect_context: FrozenMap
    schema: FrozenMap | None
    metadata: FrozenMap

    def __init__(
        self,
        name: str,
        locator: str | Sequence[str],
        detected_format: DetectedResourceFormat,
        encoding: str | None,
        dialect: Mapping[str, Any],
        dialect_context: Mapping[str, Any],
        schema: Mapping[str, Any] | None,
        metadata: Mapping[str, Any],
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "locator", _freeze_locator(locator))
        object.__setattr__(self, "detected_format", detected_format)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "dialect", _freeze_map(dialect, "dialect"))
        object.__setattr__(
            self,
            "dialect_context",
            _freeze_map(dialect_context, "dialect_context"),
        )
        object.__setattr__(
            self,
            "schema",
            None if schema is None else _freeze_map(schema, "schema"),
        )
        object.__setattr__(self, "metadata", _freeze_map(metadata, "metadata"))


@dataclass(frozen=True, init=False)
class ProviderReadResult:
    """Portable Arrow data and final dialect-planning facts."""

    table: pa.Table
    resolved_context: FrozenMap
    dialect_fields: FrozenMap

    def __init__(
        self,
        table: pa.Table,
        resolved_context: Mapping[str, Any],
        dialect_fields: Mapping[str, Any],
    ) -> None:
        object.__setattr__(self, "table", table)
        object.__setattr__(
            self,
            "resolved_context",
            _freeze_map(resolved_context, "resolved_context"),
        )
        object.__setattr__(
            self,
            "dialect_fields",
            _freeze_map(dialect_fields, "dialect_fields"),
        )


@dataclass(frozen=True, init=False)
class NativeReadRequest:
    """Optional backend acceleration request with no runtime state."""

    kind: str
    arguments: FrozenMap

    def __init__(self, kind: str, arguments: Mapping[str, Any]) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "arguments", _freeze_map(arguments, "arguments"))


def validate_dynamic_context_value(key: str, value: object) -> StructuredRowShape:
    """Validate the closed API-v1 data-dependent context contract."""
    from .errors import ProviderCompatibilityError

    if key != "structured_row_shape":
        raise ProviderCompatibilityError(f"unknown dynamic context key: {key}")
    if not isinstance(value, (str, StructuredRowShape)):
        raise ProviderCompatibilityError("structured_row_shape must be a string enum value")
    try:
        return StructuredRowShape(value)
    except ValueError as exc:
        raise ProviderCompatibilityError(f"unknown structured_row_shape: {value!r}") from exc


def _normalize_strings(
    values: Collection[str],
    field_name: str,
    normalizer: Callable[[str], str],
) -> frozenset[str]:
    return frozenset(normalizer(value) for value in _freeze_strings(values, field_name))


def _freeze_strings(values: Collection[str], field_name: str) -> frozenset[str]:
    result = frozenset(values)
    if not all(isinstance(value, str) for value in result):
        raise TypeError(f"{field_name} must contain strings")
    return result


def _freeze_locator(locator: str | Sequence[str]) -> str | tuple[str, ...]:
    if isinstance(locator, str):
        return locator
    if not isinstance(locator, Sequence):
        raise TypeError("locator must be a string or sequence of strings")
    result = tuple(locator)
    if not all(isinstance(part, str) for part in result):
        raise TypeError("locator sequence must contain strings")
    return result


def _freeze_map(value: Mapping[str, Any], field_name: str) -> FrozenMap:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return FrozenMap(value)


__all__ = [
    "DEFERRED_CONTEXT_KEYS",
    "DetectedResourceFormat",
    "DialectFieldDisposition",
    "NativeReadRequest",
    "ProviderFormatDescriptor",
    "ProviderReadResult",
    "ResourceRequest",
    "StructuredRowShape",
]
