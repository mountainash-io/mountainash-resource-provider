from __future__ import annotations

import json
from enum import auto
from typing import cast

from mountainash_resource_provider.compat import StrEnum


class Mode(StrEnum):
    EXPLICIT = "explicit-value"
    AUTOMATIC = auto()


def test_strenum_preserves_python_string_behavior() -> None:
    assert cast(str, Mode.EXPLICIT) == "explicit-value"
    assert cast(str, Mode.AUTOMATIC) == "automatic"
    assert str(Mode.EXPLICIT) == "explicit-value"
    assert f"{Mode.AUTOMATIC}" == "automatic"
    assert json.dumps({"mode": Mode.EXPLICIT}) == '{"mode": "explicit-value"}'
    assert Mode("automatic") is Mode.AUTOMATIC
    assert list(Mode) == [Mode.EXPLICIT, Mode.AUTOMATIC]
