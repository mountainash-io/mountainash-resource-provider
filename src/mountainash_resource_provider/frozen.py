"""Owned immutable values for provider boundaries."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence, Set
from dataclasses import dataclass, field
from typing import Any, TypeAlias, Union

FrozenScalar: TypeAlias = None | bool | int | float | str | bytes


@dataclass(frozen=True, repr=False)
class RedactedValue:
    """A sensitive string whose value is unavailable in diagnostics."""

    value: str = field(repr=False)
    label: str = "sensitive value"

    def reveal(self) -> str:
        """Return the sensitive value for the owning provider only."""
        return self.value

    def __repr__(self) -> str:
        return f"RedactedValue(label={self.label!r})"

    __str__ = __repr__


FrozenValue: TypeAlias = Union[
    FrozenScalar,
    RedactedValue,
    tuple["FrozenValue", ...],
    frozenset["FrozenValue"],
    "FrozenMap",
]


class FrozenMap(Mapping[str, FrozenValue]):
    """An insertion-ordered, deeply immutable mapping with owned storage."""

    __slots__ = ("_items",)

    def __init__(self, source: Mapping[str, Any]) -> None:
        self._items = tuple(
            (self._freeze_key(key), deep_freeze(value)) for key, value in source.items()
        )

    @staticmethod
    def _freeze_key(key: object) -> str:
        if not isinstance(key, str):
            raise TypeError("FrozenMap keys must be strings")
        return key

    def __getitem__(self, key: str) -> FrozenValue:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        values = ", ".join(f"{key!r}: {value!r}" for key, value in self._items)
        return f"FrozenMap({{{values}}})"

    def __hash__(self) -> int:
        return hash(self._items)


def deep_freeze(value: Any) -> FrozenValue:
    """Copy a supported boundary value into the immutable provider value family."""
    if value is None or isinstance(value, (bool, int, float, str, bytes, RedactedValue, FrozenMap)):
        return value
    if isinstance(value, Mapping):
        return FrozenMap(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, Set) and not isinstance(value, (str, bytes, bytearray)):
        return frozenset(deep_freeze(item) for item in value)
    raise TypeError(f"unsupported provider boundary value: {type(value).__qualname__}")


__all__ = ["FrozenMap", "FrozenScalar", "FrozenValue", "RedactedValue", "deep_freeze"]
