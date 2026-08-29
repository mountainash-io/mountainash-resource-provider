"""Lazy provider entry-point discovery and contract validation."""

from __future__ import annotations

import re
from importlib.metadata import EntryPoint, entry_points

from .api import RESOURCE_PROVIDER_API_VERSION
from .errors import ProviderCompatibilityError, ProviderUnavailableError
from .models import ProviderFormatDescriptor
from .protocol import ResourceProviderProtocol

ENTRY_POINT_GROUP = "mountainash.resource_providers"
_PROVIDER_KEY = re.compile(r"[a-z][a-z0-9_-]*\Z")


def validate_provider(
    provider: object,
    *,
    expected_key: str | None = None,
) -> ResourceProviderProtocol:
    """Validate one explicit or discovered API-v1 provider instance."""
    if not isinstance(provider, ResourceProviderProtocol):
        raise ProviderCompatibilityError("provider does not implement the API-v1 protocol")
    if not isinstance(provider.key, str) or _PROVIDER_KEY.fullmatch(provider.key) is None:
        raise ProviderCompatibilityError(
            "provider key must be lowercase ASCII and start with a letter"
        )
    if expected_key is not None and provider.key != expected_key:
        raise ProviderCompatibilityError(
            f"provider key {provider.key!r} does not match expected key {expected_key!r}"
        )
    if provider.api_version != RESOURCE_PROVIDER_API_VERSION:
        raise ProviderCompatibilityError(
            "provider API version "
            f"{provider.api_version!r} does not match {RESOURCE_PROVIDER_API_VERSION}"
        )
    if not isinstance(provider.formats, tuple):
        raise ProviderCompatibilityError("provider formats must be a tuple")
    if not isinstance(provider.parser_keys, frozenset):
        raise ProviderCompatibilityError("provider parser_keys must be a frozenset")
    if not all(
        isinstance(key, str) and _PROVIDER_KEY.fullmatch(key) for key in provider.parser_keys
    ):
        raise ProviderCompatibilityError("provider parser keys must be lowercase ASCII identifiers")
    for descriptor in provider.formats:
        if not isinstance(descriptor, ProviderFormatDescriptor):
            raise ProviderCompatibilityError(
                "provider formats must contain ProviderFormatDescriptor values"
            )
        if descriptor.provider_format_key not in provider.parser_keys:
            raise ProviderCompatibilityError(
                f"format {descriptor.canonical_format!r} names an unknown parser key"
            )
    return provider


def iter_provider_entry_points() -> tuple[EntryPoint, ...]:
    """Return API-v1 provider entry points without loading their factories."""
    available = entry_points()
    return tuple(available.select(group=ENTRY_POINT_GROUP))


def load_provider_by_key(key: str) -> ResourceProviderProtocol:
    """Load only the named provider entry point."""
    matches = tuple(
        entry_point
        for entry_point in iter_provider_entry_points()
        if entry_point.name == key
    )
    if not matches:
        raise ProviderUnavailableError(f"resource provider {key!r} is not installed")
    if len(matches) != 1:
        raise ProviderCompatibilityError(f"duplicate resource-provider entry-point name: {key!r}")
    return _load_entry_point(matches[0], expected_key=key)


def load_all_providers() -> tuple[ResourceProviderProtocol, ...]:
    """Load and validate every installed provider entry point."""
    entries = iter_provider_entry_points()
    names = [entry_point.name for entry_point in entries]
    if len(names) != len(set(names)):
        raise ProviderCompatibilityError("duplicate resource-provider entry-point names")
    providers = tuple(
        _load_entry_point(entry_point, expected_key=entry_point.name)
        for entry_point in entries
    )
    keys = [provider.key for provider in providers]
    if len(keys) != len(set(keys)):
        raise ProviderCompatibilityError("duplicate resource-provider keys")
    return providers


def _load_entry_point(entry_point: EntryPoint, *, expected_key: str) -> ResourceProviderProtocol:
    try:
        factory = entry_point.load()
        provider = factory()
    except ProviderCompatibilityError:
        raise
    except Exception as exc:
        raise ProviderCompatibilityError(
            f"could not construct resource provider {expected_key!r}"
        ) from exc
    return validate_provider(provider, expected_key=expected_key)


__all__ = [
    "ENTRY_POINT_GROUP",
    "iter_provider_entry_points",
    "load_all_providers",
    "load_provider_by_key",
    "validate_provider",
]
