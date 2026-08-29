from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from mountainash_resource_provider.api import RESOURCE_PROVIDER_API_VERSION, ReaderBackend
from mountainash_resource_provider.frozen import FrozenMap
from mountainash_resource_provider.models import (
    DetectedResourceFormat,
    NativeReadRequest,
    ProviderFormatDescriptor,
    ProviderReadResult,
    ResourceRequest,
)
from mountainash_resource_provider.protocol import ProviderReadPlan
from mountainash_resource_provider.testing import (
    compare_provider_equivalence,
    run_provider_contract,
)


@dataclass(frozen=True)
class Plan:
    provider_key: str
    dialect_fields: FrozenMap
    payload: FrozenMap


class ContractProvider:
    key: str = "file"
    api_version: int = RESOURCE_PROVIDER_API_VERSION
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
    parser_keys: frozenset[str] = frozenset({"csv"})

    def plan(self, request: ResourceRequest) -> Plan:
        return Plan(
            provider_key=self.key,
            dialect_fields=FrozenMap({"header": "consumed"}),
            payload=FrozenMap({"locator": request.locator}),
        )

    def read_arrow(self, plan: ProviderReadPlan) -> ProviderReadResult:
        return ProviderReadResult(
            table=pa.table({"id": [1]}),
            resolved_context={},
            dialect_fields=plan.dialect_fields,
        )

    def native_request(
        self,
        plan: ProviderReadPlan,
        backend: ReaderBackend,
    ) -> NativeReadRequest | None:
        if backend is ReaderBackend.POLARS:
            return NativeReadRequest(kind="csv", arguments=plan.payload)
        return None


def request() -> ResourceRequest:
    return ResourceRequest(
        name="records",
        locator="records.csv",
        detected_format=DetectedResourceFormat(
            canonical_format="csv",
            dialect_family="delimited",
            provider_format_key="csv",
            detection_source="suffix",
        ),
        encoding="utf-8",
        dialect={"header": True},
        dialect_context={},
        schema=None,
        metadata={},
    )


def test_provider_contract_runs_without_errors() -> None:
    results = run_provider_contract(lambda: ContractProvider(), [request()])

    assert results
    assert all(result.error is None for result in results)


def test_equivalence_compares_all_provider_boundaries() -> None:
    rows = compare_provider_equivalence(
        ContractProvider(),
        ContractProvider(),
        request(),
        (ReaderBackend.POLARS, ReaderBackend.NARWHALS, ReaderBackend.IBIS),
    )

    assert rows
    assert all(row.equivalent for row in rows)
