"""The API-v1 resource-provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .api import ReaderBackend
from .frozen import FrozenMap
from .models import (
    NativeReadRequest,
    ProviderFormatDescriptor,
    ProviderReadResult,
    ResourceRequest,
)


@runtime_checkable
class ProviderReadPlan(Protocol):
    """An immutable provider-owned plan for exactly one request."""

    @property
    def provider_key(self) -> str:
        """Return the key of the provider that owns this plan."""
        ...

    @property
    def dialect_fields(self) -> FrozenMap:
        """Return immutable dialect-field dispositions."""
        ...

    @property
    def payload(self) -> FrozenMap:
        """Return immutable provider-owned plan data."""
        ...


@runtime_checkable
class ResourceProviderProtocol(Protocol):
    """A discovered resource provider with a portable Arrow read path."""

    key: str
    api_version: int
    formats: tuple[ProviderFormatDescriptor, ...]
    parser_keys: frozenset[str]

    def plan(self, request: ResourceRequest) -> ProviderReadPlan:
        """Create an immutable read plan without resource access."""

    def read_arrow(self, plan: ProviderReadPlan) -> ProviderReadResult:
        """Read the portable Arrow result for a plan."""

    def native_request(
        self,
        plan: ProviderReadPlan,
        backend: ReaderBackend,
    ) -> NativeReadRequest | None:
        """Return an optional backend acceleration request."""


__all__ = ["ProviderReadPlan", "ResourceProviderProtocol"]
