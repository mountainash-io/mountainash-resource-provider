# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Design Principles — READ FIRST

Durable architectural decisions for this package live in **mountainash-central**:

```
mountainash-central/01.principles/mountainash-resource-provider/
├── PRINCIPLES.md                      # governance: categories, status markers, how to add a principle
├── README.md                          # index of principles by category
├── a.architecture/                    # ENFORCED/ADOPTED — dependency inversion, entry-point
│                                       #   discovery, provider-owned plans, Arrow portable result,
│                                       #   deep-ownership boundary values
├── b.contract-and-versioning/         # PROPOSED — strict boundary validation, validated provider
│                                       #   catalog, protocol version negotiation
├── c.security-and-errors/             # ADOPTED/PROPOSED — display redaction vs. access control,
│                                       #   structured error context
├── d.execution-lifecycle/             # ADOPTED/PROPOSED — snapshot execution contract, native
│                                       #   request identity and lifecycle
└── e.development-practices/           # ADOPTED/PROPOSED — provider contract test kit, alpha/
                                        #   first-party scope, package and release governance
```

(Sibling repo — typically `../mountainash-central/01.principles/mountainash-resource-provider/`.)

Before changing a boundary model (`ResourceRequest`, `ProviderReadPlan`, `ProviderReadResult`,
`NativeReadRequest`, `ProviderFormatDescriptor`, `RedactedValue`, `FrozenMap`), discovery/validation
(`discovery.py`), or the public protocol (`protocol.py`), read the relevant principle. Key ones in
force:

- **Dependency Inversion (ENFORCED):** zero dependency on `mountainash`, `mountainash-files`, or
  `mountainash-data`. Never add one to make a specific provider "just work."
- **Entry-Point Discovery (ENFORCED):** the `mountainash.resource_providers` entry-point group is
  the only discovery mechanism. One provider is selected per resource — never adopt a multi-hook
  plugin manager (Pluggy or similar).
- **Deep Ownership of Boundary Values (ADOPTED):** every mutable input crossing a provider boundary
  goes through `deep_freeze()` into `FrozenMap`. Never let a connection, settings object, or
  callable cross a boundary.
- **Display Redaction, Not Access Control (ADOPTED):** `RedactedValue` hides a secret from `repr()`/
  `str()`. It is not a capability boundary — `reveal()` always returns the raw value. Never document
  or rely on it as access control.
- **Alpha, First-Party Scope (ADOPTED):** this SPI is safe today only for trusted, coordinated-
  version, first-party providers. It is not a third-party plugin contract until the SPI-1/2/4/5/7
  hardening items land (see Backlog below).

## Backlog — SPI Hardening Program

The [2026-08-31 SPI architectural review](../mountainash-central/04.planning/mountainash/superpowers/reviews/2026-08-31-resource-provider-spi-architectural-review.md)
found the SPI's architecture sound but its implementation not yet enforcing the contract its types
describe. The required hardening is tracked as a seven-item series:

See [INDEX.md](../mountainash-central/04.planning/mountainash-resource-provider/a.backlog/INDEX.md)
for priorities, dependency order, and status. Summary:

| Item | What | Priority | Depends on |
|------|------|----------|------------|
| SPI-1 | Strict boundary models — every constructor rejects invalid runtime state | P0 | — |
| SPI-2 | Validated provider catalog and registration — immutable snapshot + global conflict detection | P0 | SPI-1 |
| SPI-3 | Protocol version and feature negotiation — major/minor version, not exact-equality | P1 | SPI-1 |
| SPI-4 | Security and structured error boundary — redaction threat model, structured `ProviderError` fields | P0 | SPI-1 |
| SPI-5 | Provider conformance certification kit — strict `assert_provider_contract()`, cannot pass by omission | P0 | SPI-1, 2, 3, 4, 6 |
| SPI-6 | Execution lifecycle, batches, native request identity — namespaced `<provider-key>/<kind>@<version>` | P1 | SPI-3, 4 |
| SPI-7 | Package, CI, and release governance — CI matrix, license, security policy, changelog | P0 before external publication | — |

### Keeping the backlog current

After every change that closes or reshapes an SPI item — merging a PR, landing part of an item,
discovering a new gap — update
`mountainash-central/04.planning/mountainash-resource-provider/a.backlog/INDEX.md` and the item's own
file:

- Mark completed items ✅ with the PR number and merge date.
- Update the dependency-order diagram if a new item is added or a dependency changes.
- Promote the corresponding principle's status marker (`PROPOSED` → `ADOPTED` → `ENFORCED`) in
  `01.principles/mountainash-resource-provider/` once the code and tests catch up — do this in the
  same PR that lands the item, not as a follow-up.

## Superpowers Specs & Plans Location

Save all superpowers specs and plans to the **mountainash-central** repo, not this repo:

- **Specs:** `mountainash-central/04.planning/mountainash-resource-provider/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- **Plans:** `mountainash-central/04.planning/mountainash-resource-provider/superpowers/plans/YYYY-MM-DD-<topic>.md`

Never save specs or plans under `docs/superpowers/` in this repo. The central repo is the single
source of truth for all planning documents. Only source, tests, and this `CLAUDE.md` live in this
repo's tree.

## Project Overview

**mountainash-resource-provider** defines the neutral API-v1 SPI (service provider interface) for
packages that acquire tabular resources on Mountainash's behalf — a file path, database locator,
URL, or API endpoint. It has no dependency on Mountainash or any provider package; provider packages
(`mountainash-files`, `mountainash-data`) depend on it instead.

A provider publishes immutable format descriptors and parser keys, produces an immutable
`ProviderReadPlan` per request, and supplies a portable `pyarrow.Table` result through
`read_arrow()`. An optional `native_request()` can offer a backend-specific acceleration, but it can
never be the only correctness path — every provider must have a working Arrow route.

**Current status:** alpha, first-party only (see `pyproject.toml` classifiers). See
[`alpha-first-party-scope.md`](../mountainash-central/01.principles/mountainash-resource-provider/e.development-practices/alpha-first-party-scope.md)
for the exact conditions under which this is safe to use.

## Package Structure

```
src/mountainash_resource_provider/
├── __init__.py       # public API surface (+ __all__)
├── api.py             # RESOURCE_PROVIDER_API_VERSION, ReaderBackend
├── compat.py          # StrEnum compatibility shim
├── discovery.py       # entry-point discovery + validate_provider()
├── errors.py          # ProviderError hierarchy (availability, compatibility, configuration,
│                       #   dependency, format, dialect capability/value, backend capability, read)
├── formats.py         # format-token normalization
├── frozen.py          # FrozenMap, RedactedValue, deep_freeze() — the owned immutable value family
├── models.py          # ResourceRequest, ProviderReadResult, NativeReadRequest,
│                       #   ProviderFormatDescriptor, DetectedResourceFormat, dialect dispositions
├── protocol.py         # ProviderReadPlan / ResourceProviderProtocol — the public contract
└── testing.py          # run_provider_contract(), compare_provider_equivalence() — diagnostic
                          #   contract helpers (not yet a certification gate; see SPI-5)
```

## Provider API

Providers expose a zero-argument factory in the `mountainash.resource_providers` entry-point group.
The entry-point name and the provider `key` must match exactly:

```toml
[project.entry-points."mountainash.resource_providers"]
file = "mountainash_files.provider:create_provider"
```

The provider must declare `api_version = RESOURCE_PROVIDER_API_VERSION`. It must not read a
resource, resolve settings, open a connection, or import an optional reader SDK when the factory
runs.

## Security Boundary

Use `RedactedValue` for sensitive strings. Do not put credentials, direct database URLs, API
tokens, settings objects, connection objects, or callables in a request, plan, native request,
result context, or diagnostic. `deep_freeze()` rejects unsupported mutable boundary values, but does
not — today — identify a secret embedded in an ordinary string; see
[`display-redaction-not-access-control.md`](../mountainash-central/01.principles/mountainash-resource-provider/c.security-and-errors/display-redaction-not-access-control.md).

## Build / Test / Lint

This package uses **hatch** (with `uv` as the installer).

- Tests: `hatch run test:test` (single file/test: `hatch run test:test <path>::<test> -v`)
- Lint: `hatch run ruff:check` (auto-fix: `hatch run ruff:fix`)
- Type check: `hatch run mypy:check` (strict mode, `src` and `tests`)
- Build: `hatch build`

The Hatch test matrix currently runs Python 3.12 only; `pyproject.toml` classifiers claim 3.10–3.12.
Closing that gap is tracked as SPI-7.

## Conventions

- **Code style:** ruff formatting (`E`, `F`, `I`, `UP` rule sets, line length 100), `from __future__
  import annotations`, full type annotations (mypy strict).
- **Immutability:** every dataclass at a provider boundary is `@dataclass(frozen=True)`; mutable
  inputs are copied through `deep_freeze()`/`FrozenMap`, never stored by reference.
- **Contract testing:** use `run_provider_contract()` and `compare_provider_equivalence()` from
  `testing.py` during provider development, but do not present a passing run as SPI certification —
  see the provider-contract-test-kit principle above.

## Git Branch Flow (mountainash three-tier)

```
feature/* | bugfix/* | hotfix/* | docs/* | chore/*  →  develop  →  release/*  →  main + tag
```

Feature/bugfix/hotfix/docs PRs **always target `develop`**. Never push directly to `develop` or
`main`. CalVer `YY.MM.MICRO` for releases.
