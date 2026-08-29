"""Errors raised at the neutral resource-provider boundary."""


class ProviderError(Exception):
    """Base class for provider boundary failures."""


class ProviderUnavailableError(ProviderError, ImportError):
    """A requested provider is unavailable."""


class ProviderCompatibilityError(ProviderError, RuntimeError):
    """A provider does not satisfy the API contract."""


class ProviderConfigurationError(ProviderError, ValueError):
    """A provider configuration is invalid."""


class ProviderDependencyError(ProviderError, ImportError):
    """An optional provider dependency is unavailable."""


class ProviderFormatError(ProviderError, ValueError):
    """A provider cannot resolve a resource format."""


class ProviderDialectCapabilityError(ProviderError, ValueError):
    """A provider does not support a dialect capability."""


class ProviderDialectValueError(ProviderError, ValueError):
    """A dialect value is invalid for its provider."""


class ProviderBackendCapabilityError(ProviderError, NotImplementedError):
    """A provider cannot supply a requested backend acceleration."""


class ProviderReadError(ProviderError, RuntimeError):
    """A provider cannot read the requested resource."""


__all__ = [
    "ProviderBackendCapabilityError",
    "ProviderCompatibilityError",
    "ProviderConfigurationError",
    "ProviderDependencyError",
    "ProviderDialectCapabilityError",
    "ProviderDialectValueError",
    "ProviderError",
    "ProviderFormatError",
    "ProviderReadError",
    "ProviderUnavailableError",
]
