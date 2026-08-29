from __future__ import annotations

import pytest

from mountainash_resource_provider.errors import (
    ProviderBackendCapabilityError,
    ProviderCompatibilityError,
    ProviderConfigurationError,
    ProviderDependencyError,
    ProviderDialectCapabilityError,
    ProviderDialectValueError,
    ProviderError,
    ProviderFormatError,
    ProviderReadError,
    ProviderUnavailableError,
)

CASES = [
    (ProviderUnavailableError, ImportError),
    (ProviderCompatibilityError, RuntimeError),
    (ProviderConfigurationError, ValueError),
    (ProviderDependencyError, ImportError),
    (ProviderFormatError, ValueError),
    (ProviderDialectCapabilityError, ValueError),
    (ProviderDialectValueError, ValueError),
    (ProviderBackendCapabilityError, NotImplementedError),
    (ProviderReadError, RuntimeError),
]


@pytest.mark.parametrize(("leaf", "builtin"), CASES)
def test_error_leaf_contract(
    leaf: type[ProviderError], builtin: type[Exception]
) -> None:
    error = leaf("failure")

    assert isinstance(error, ProviderError)
    assert isinstance(error, builtin)
