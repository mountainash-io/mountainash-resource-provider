from __future__ import annotations

import pytest

from mountainash_resource_provider.errors import (
    ProviderCompatibilityError,
    ProviderFormatError,
)
from mountainash_resource_provider.formats import (
    normalize_format_name,
    normalize_locator_prefix,
    normalize_mediatype,
    normalize_suffix,
)
from mountainash_resource_provider.models import (
    DEFERRED_CONTEXT_KEYS,
    ProviderFormatDescriptor,
    StructuredRowShape,
    validate_dynamic_context_value,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(" CSV ", "csv"), ("GeoJSON", "geojson")],
)
def test_normalize_format_name(raw: str, expected: str) -> None:
    assert normalize_format_name(raw) == expected


@pytest.mark.parametrize("raw", ["csv", ".CSV", "..csv"])
def test_normalize_suffix(raw: str) -> None:
    assert normalize_suffix(raw) == ".csv"


@pytest.mark.parametrize("raw", ["TEXT/CSV", " text/csv ; charset=utf-8 "])
def test_normalize_mediatype(raw: str) -> None:
    assert normalize_mediatype(raw) == "text/csv"


def test_normalize_locator_prefix_changes_scheme_only() -> None:
    assert normalize_locator_prefix("DUCKDB://md:Case") == "duckdb://md:Case"


@pytest.mark.parametrize("raw", ["", "not a format", "text/csv"])
def test_format_name_rejects_invalid_identifiers(raw: str) -> None:
    with pytest.raises(ProviderFormatError):
        normalize_format_name(raw)


@pytest.mark.parametrize("raw", ["text/csv; charset=utf-8", "te xt/csv", "text"])
def test_mediatype_rejects_published_parameters_and_invalid_tokens(raw: str) -> None:
    with pytest.raises(ProviderFormatError):
        normalize_mediatype(raw, published=True)


def test_descriptor_normalizes_all_published_tokens() -> None:
    descriptor = ProviderFormatDescriptor(
        canonical_format=" CSV ",
        aliases={"Comma-Separated"},
        suffixes={"CSV"},
        mediatypes={"TEXT/CSV"},
        locator_prefixes={"FILE://case-sensitive"},
        dialect_family="delimited",
        provider_format_key="csv",
    )

    assert descriptor.canonical_format == "csv"
    assert descriptor.aliases == frozenset({"comma-separated"})
    assert descriptor.suffixes == frozenset({".csv"})
    assert descriptor.mediatypes == frozenset({"text/csv"})
    assert descriptor.locator_prefixes == frozenset({"file://case-sensitive"})


def test_dynamic_context_contract_is_closed() -> None:
    assert DEFERRED_CONTEXT_KEYS == frozenset({"structured_row_shape"})
    assert (
        validate_dynamic_context_value("structured_row_shape", "object")
        is StructuredRowShape.OBJECT
    )
    assert (
        validate_dynamic_context_value("structured_row_shape", "array")
        is StructuredRowShape.ARRAY
    )
    assert (
        validate_dynamic_context_value("structured_row_shape", "empty")
        is StructuredRowShape.EMPTY
    )

    with pytest.raises(ProviderCompatibilityError):
        validate_dynamic_context_value("unknown", "object")
    with pytest.raises(ProviderCompatibilityError):
        validate_dynamic_context_value("structured_row_shape", object())
    with pytest.raises(ProviderCompatibilityError):
        validate_dynamic_context_value("structured_row_shape", "scalar")
