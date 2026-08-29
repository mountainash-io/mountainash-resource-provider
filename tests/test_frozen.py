from __future__ import annotations

from dataclasses import FrozenInstanceError

import pyarrow as pa
import pytest

from mountainash_resource_provider.frozen import FrozenMap, RedactedValue, deep_freeze
from mountainash_resource_provider.models import (
    DetectedResourceFormat,
    NativeReadRequest,
    ProviderFormatDescriptor,
    ProviderReadResult,
    ResourceRequest,
)


def test_deep_freeze_owns_nested_inputs() -> None:
    items = [{"name": "a"}]
    flags = {"x"}
    source: dict[str, object] = {"items": items, "flags": flags}

    frozen = deep_freeze(source)
    items[0]["name"] = "changed"
    flags.add("y")

    assert frozen == FrozenMap(
        {"items": (FrozenMap({"name": "a"}),), "flags": frozenset({"x"})}
    )


def test_redacted_value_hides_sensitive_text() -> None:
    value = RedactedValue("postgresql://user:secret@host/db", label="database URL")

    assert "secret" not in repr(value)
    assert "secret" not in str(value)
    assert value.reveal() == "postgresql://user:secret@host/db"


@pytest.mark.parametrize(
    "value",
    [lambda: None, object(), {"callable": lambda: None}],
)
def test_deep_freeze_rejects_non_boundary_values(value: object) -> None:
    with pytest.raises(TypeError):
        deep_freeze(value)


def test_boundary_models_own_mutable_inputs() -> None:
    aliases = {"comma-separated"}
    suffixes = {".csv"}
    header_rows = [1]
    request_dialect: dict[str, object] = {"header": True, "headerRows": header_rows}
    request_context: dict[str, object] = {"family": "delimited"}
    schema_fields = [{"name": "id"}]
    schema: dict[str, object] = {"fields": schema_fields}
    labels = {"id"}
    metadata: dict[str, object] = {"custom": {"labels": labels}}
    options = {"header": True}
    native_arguments: dict[str, object] = {"options": options}

    descriptor = ProviderFormatDescriptor(
        canonical_format="csv",
        aliases=aliases,
        suffixes=suffixes,
        mediatypes={"text/csv"},
        locator_prefixes=set[str](),
        dialect_family="delimited",
        provider_format_key="csv",
    )
    request = ResourceRequest(
        name="records",
        locator=("records.csv",),
        detected_format=DetectedResourceFormat(
            canonical_format="csv",
            dialect_family="delimited",
            provider_format_key="csv",
            detection_source="suffix",
        ),
        encoding="utf-8",
        dialect=request_dialect,
        dialect_context=request_context,
        schema=schema,
        metadata=metadata,
    )
    result = ProviderReadResult(
        table=pa.table({"id": [1]}),
        resolved_context={"structured_row_shape": "object"},
        dialect_fields={"header": "consumed"},
    )
    native_request = NativeReadRequest(kind="csv", arguments=native_arguments)

    aliases.add("changed")
    suffixes.add(".txt")
    header_rows.append(2)
    schema_fields[0]["name"] = "changed"
    labels.add("changed")
    options["header"] = False

    assert descriptor.aliases == frozenset({"comma-separated"})
    assert descriptor.suffixes == frozenset({".csv"})
    assert request.dialect == FrozenMap({"header": True, "headerRows": (1,)})
    assert request.schema == FrozenMap({"fields": (FrozenMap({"name": "id"}),)})
    assert request.metadata == FrozenMap({"custom": FrozenMap({"labels": frozenset({"id"})})})
    assert native_request.arguments == FrozenMap({"options": FrozenMap({"header": True})})
    assert result.resolved_context == FrozenMap({"structured_row_shape": "object"})

    with pytest.raises(FrozenInstanceError):
        request.name = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.dialect["header"] = False  # type: ignore[index]
