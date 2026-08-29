# mountainash-resource-provider

`mountainash-resource-provider` defines API-v1 contracts for packages that read
tabular resources for Mountainash.

## Provider API

Providers expose a zero-argument factory in the
`mountainash.resource_providers` entry-point group. The entry-point name and
the provider `key` must match exactly. Each provider exposes immutable format
descriptors, produces an immutable plan, and supplies a portable
`pyarrow.Table` result.

```toml
[project.entry-points."mountainash.resource_providers"]
file = "mountainash_files.provider:create_provider"
```

The provider must declare `api_version = RESOURCE_PROVIDER_API_VERSION`. It
must not read a resource, resolve settings, open a connection, or import an
optional reader SDK when the factory runs.

## Security boundary

Use `RedactedValue` for sensitive strings. Do not put credentials, direct
database URLs, settings objects, connection objects, or callables in a
request, plan, native request, result context, or diagnostic. `deep_freeze()`
rejects unsupported mutable boundary values.

## Contract tests

Use `run_provider_contract()` with a provider factory and representative
`ResourceRequest` values. Use `compare_provider_equivalence()` to compare
provider objects, plans, native requests, Arrow output, and error behavior.
Run the provider package tests on Python 3.10 and 3.12 before publishing.
