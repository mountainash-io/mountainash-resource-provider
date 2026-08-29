"""Reusable, dependency-free resource-provider contract checks."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .api import ReaderBackend
from .discovery import validate_provider
from .frozen import FrozenMap
from .models import (
    DEFERRED_CONTEXT_KEYS,
    DialectFieldDisposition,
    NativeReadRequest,
    ProviderReadResult,
    ResourceRequest,
    validate_dynamic_context_value,
)
from .protocol import ProviderReadPlan, ResourceProviderProtocol


@dataclass(frozen=True)
class ContractResult:
    """One provider-contract outcome."""

    check: str
    request_name: str | None
    error: str | None


@dataclass(frozen=True)
class EquivalenceResult:
    """One comparison across the provider boundary."""

    boundary: str
    equivalent: bool


def run_provider_contract(
    provider_factory: Callable[[], object],
    probes: Iterable[ResourceRequest],
) -> tuple[ContractResult, ...]:
    """Run API-v1 checks against a provider factory and concrete requests."""
    results: list[ContractResult] = []
    try:
        provider = validate_provider(provider_factory())
    except Exception as exc:
        return (ContractResult("factory", None, _error_text(exc)),)
    results.append(ContractResult("factory", None, None))

    for request in probes:
        try:
            plan = provider.plan(request)
            _validate_plan(provider, plan, request)
            results.append(ContractResult("plan", request.name, None))
        except Exception as exc:
            results.append(ContractResult("plan", request.name, _error_text(exc)))
            continue
        try:
            _validate_result(provider.read_arrow(plan), plan, request)
            results.append(ContractResult("arrow", request.name, None))
        except Exception as exc:
            results.append(ContractResult("arrow", request.name, _error_text(exc)))
        for backend in ReaderBackend:
            try:
                native = provider.native_request(plan, backend)
                if native is not None and not isinstance(native, NativeReadRequest):
                    raise TypeError("native_request must return NativeReadRequest or None")
                if _has_deferred(plan) and native is not None:
                    raise ValueError("native_request cannot accelerate a deferred plan")
                results.append(ContractResult(f"native:{backend}", request.name, None))
            except Exception as exc:
                results.append(
                    ContractResult(f"native:{backend}", request.name, _error_text(exc))
                )
    return tuple(results)


def compare_provider_equivalence(
    left: ResourceProviderProtocol,
    right: ResourceProviderProtocol,
    request: ResourceRequest,
    backends: Iterable[ReaderBackend],
) -> tuple[EquivalenceResult, ...]:
    """Compare provider objects, plans, native requests, Arrow output, and errors."""
    rows = [
        EquivalenceResult("object", _provider_identity(left) == _provider_identity(right)),
    ]
    left_plan = _capture(lambda: left.plan(request))
    right_plan = _capture(lambda: right.plan(request))
    rows.append(EquivalenceResult("plan", _same_capture(left_plan, right_plan)))
    if not left_plan[0] or not right_plan[0]:
        return tuple(rows)

    left_plan_value = left_plan[1]
    right_plan_value = right_plan[1]
    for backend in backends:
        left_native = _capture(lambda: left.native_request(left_plan_value, backend))
        right_native = _capture(lambda: right.native_request(right_plan_value, backend))
        rows.append(
            EquivalenceResult(f"native:{backend}", _same_capture(left_native, right_native))
        )

    left_arrow = _capture(lambda: left.read_arrow(left_plan_value))
    right_arrow = _capture(lambda: right.read_arrow(right_plan_value))
    rows.append(EquivalenceResult("arrow", _same_arrow_capture(left_arrow, right_arrow)))
    return tuple(rows)


def _validate_plan(
    provider: ResourceProviderProtocol,
    plan: ProviderReadPlan,
    request: ResourceRequest,
) -> None:
    if not _is_plan(plan):
        raise TypeError("plan does not implement ProviderReadPlan")
    if plan.provider_key != provider.key:
        raise ValueError("plan provider_key does not match provider key")
    expected_fields = set(request.dialect).difference({"$schema"})
    if not expected_fields.issubset(plan.dialect_fields):
        raise ValueError("plan does not declare every dialect field")
    _validate_dispositions(plan.dialect_fields, allow_deferred=True)


def _validate_result(
    result: ProviderReadResult,
    plan: ProviderReadPlan,
    request: ResourceRequest,
) -> None:
    if not isinstance(result, ProviderReadResult):
        raise TypeError("read_arrow must return ProviderReadResult")
    if set(result.resolved_context).difference(DEFERRED_CONTEXT_KEYS):
        raise ValueError("result resolves an unsupported dynamic context key")
    for key, value in result.resolved_context.items():
        validate_dynamic_context_value(key, value)
    expected_fields = set(request.dialect).difference({"$schema"})
    if not expected_fields.issubset(result.dialect_fields):
        raise ValueError("result does not declare every dialect field")
    _validate_dispositions(result.dialect_fields, allow_deferred=False)
    if _has_deferred(plan) and not result.resolved_context:
        raise ValueError("deferred planning requires a final dynamic context update")


def _validate_dispositions(fields: FrozenMap, *, allow_deferred: bool) -> None:
    for value in fields.values():
        disposition = _as_disposition(value)
        if disposition is DialectFieldDisposition.DEFERRED and not allow_deferred:
            raise ValueError("final result cannot contain deferred disposition")


def _has_deferred(plan: ProviderReadPlan) -> bool:
    return any(
        _as_disposition(value) is DialectFieldDisposition.DEFERRED
        for value in plan.dialect_fields.values()
    )


def _as_disposition(value: object) -> DialectFieldDisposition:
    if not isinstance(value, str):
        raise ValueError("dialect disposition must be a string enum value")
    try:
        return DialectFieldDisposition(value)
    except ValueError as exc:
        raise ValueError("invalid dialect disposition") from exc


def _is_plan(value: object) -> bool:
    return (
        hasattr(value, "provider_key")
        and hasattr(value, "dialect_fields")
        and isinstance(getattr(value, "dialect_fields"), FrozenMap)
        and hasattr(value, "payload")
        and isinstance(getattr(value, "payload"), FrozenMap)
    )


def _provider_identity(provider: ResourceProviderProtocol) -> tuple[Any, ...]:
    return provider.key, provider.api_version, provider.formats, provider.parser_keys


def _capture(call: Callable[[], Any]) -> tuple[bool, Any]:
    try:
        return True, call()
    except Exception as exc:
        return False, (type(exc), _error_text(exc))


def _same_capture(left: tuple[bool, Any], right: tuple[bool, Any]) -> bool:
    return left == right


def _same_arrow_capture(left: tuple[bool, Any], right: tuple[bool, Any]) -> bool:
    if left[0] != right[0]:
        return False
    if not left[0]:
        return left == right
    left_result = left[1]
    right_result = right[1]
    return (
        isinstance(left_result, ProviderReadResult)
        and isinstance(right_result, ProviderReadResult)
        and left_result.table.equals(right_result.table)
        and left_result.resolved_context == right_result.resolved_context
        and left_result.dialect_fields == right_result.dialect_fields
    )


def _error_text(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


__all__ = [
    "ContractResult",
    "EquivalenceResult",
    "compare_provider_equivalence",
    "run_provider_contract",
]
