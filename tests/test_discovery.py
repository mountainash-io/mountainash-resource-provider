from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

import mountainash_resource_provider.discovery as discovery
from mountainash_resource_provider.api import RESOURCE_PROVIDER_API_VERSION, ReaderBackend
from mountainash_resource_provider.errors import (
    ProviderCompatibilityError,
    ProviderUnavailableError,
)
from mountainash_resource_provider.frozen import FrozenMap
from mountainash_resource_provider.models import (
    NativeReadRequest,
    ProviderFormatDescriptor,
    ProviderReadResult,
    ResourceRequest,
)


@dataclass(frozen=True)
class Plan:
    provider_key: str
    dialect_fields: FrozenMap
    payload: FrozenMap


class Provider:
    api_version = RESOURCE_PROVIDER_API_VERSION
    formats: tuple[ProviderFormatDescriptor, ...] = (
        ProviderFormatDescriptor(
            canonical_format="csv",
            aliases=frozenset(),
            suffixes=frozenset({".csv"}),
            mediatypes=frozenset({"text/csv"}),
            locator_prefixes=frozenset(),
            dialect_family="delimited",
            provider_format_key="csv",
        ),
    )
    parser_keys = frozenset({"csv"})

    def __init__(self, key: str = "file") -> None:
        self.key = key

    def plan(self, request: ResourceRequest) -> Plan:
        raise NotImplementedError

    def read_arrow(self, plan: Plan) -> ProviderReadResult:
        raise NotImplementedError

    def native_request(self, plan: Plan, backend: ReaderBackend) -> NativeReadRequest | None:
        raise NotImplementedError


class FakeEntryPoint:
    def __init__(self, name: str, factory: Callable[[], object]) -> None:
        self.name = name
        self._factory = factory
        self.loaded = False

    def load(self) -> Callable[[], object]:
        self.loaded = True
        return self._factory


class FakeEntryPoints:
    def __init__(self, entries: list[FakeEntryPoint]) -> None:
        self._entries = entries

    def select(self, *, group: str) -> list[FakeEntryPoint]:
        assert group == "mountainash.resource_providers"
        return self._entries


def install_entry_points(monkeypatch: pytest.MonkeyPatch, entries: list[FakeEntryPoint]) -> None:
    monkeypatch.setattr(discovery, "entry_points", lambda: FakeEntryPoints(entries))


def test_explicit_key_loads_only_matching_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    selected = FakeEntryPoint("file", Provider)
    unrelated = FakeEntryPoint("database", lambda: (_ for _ in ()).throw(AssertionError("loaded")))
    install_entry_points(monkeypatch, [selected, unrelated])

    provider = discovery.load_provider_by_key("file")

    assert provider.key == "file"
    assert selected.loaded is True
    assert unrelated.loaded is False


def test_explicit_key_reports_no_matching_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    install_entry_points(monkeypatch, [])

    with pytest.raises(ProviderUnavailableError):
        discovery.load_provider_by_key("file")


def test_duplicate_entry_point_names_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_entry_points(
        monkeypatch,
        [FakeEntryPoint("file", Provider), FakeEntryPoint("file", Provider)],
    )

    with pytest.raises(ProviderCompatibilityError):
        discovery.load_provider_by_key("file")


def test_provider_key_must_match_entry_point_name(monkeypatch: pytest.MonkeyPatch) -> None:
    install_entry_points(monkeypatch, [FakeEntryPoint("file", lambda: Provider("different"))])

    with pytest.raises(ProviderCompatibilityError):
        discovery.load_provider_by_key("file")


def test_validate_provider_rejects_descriptor_parser_key_mismatch() -> None:
    provider = Provider()
    provider.formats = (
        ProviderFormatDescriptor(
            canonical_format="csv",
            aliases=frozenset(),
            suffixes=frozenset({".csv"}),
            mediatypes=frozenset({"text/csv"}),
            locator_prefixes=frozenset(),
            dialect_family="delimited",
            provider_format_key="unknown",
        ),
    )

    with pytest.raises(ProviderCompatibilityError):
        discovery.validate_provider(provider)


def test_validate_provider_rejects_ambiguous_format_tokens() -> None:
    provider = Provider()
    provider.formats = (
        Provider.formats[0],
        ProviderFormatDescriptor(
            canonical_format="tsv",
            aliases=frozenset({"csv"}),
            suffixes=frozenset({".tsv"}),
            mediatypes=frozenset({"text/tab-separated-values"}),
            locator_prefixes=frozenset(),
            dialect_family="delimited",
            provider_format_key="csv",
        ),
    )

    with pytest.raises(ProviderCompatibilityError):
        discovery.validate_provider(provider)
