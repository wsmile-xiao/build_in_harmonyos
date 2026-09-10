# DRAFT-coinutils-optional-solver-backend-boundary

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

CoinUtils is a base COIN-OR utility library. Its configure scripts can probe for
additional numeric or solver-adjacent libraries such as BLAS, LAPACK, GLPK, and
ASL. Those probes are optional for the core sparse matrix and utility API.

On HarmonyOS package CI, leaving these probes open can silently widen the
dependency graph.

## Root Cause

The one-library-one-PR workflow requires missing dependencies to be adapted
separately. Optional configure probes can violate that boundary in two ways:

- link to system libraries outside the Conan graph
- fail after discovering headers or libraries that are incomplete on the target

For CoinUtils 2.11.12, W0 found existing archive coverage for the mandatory
compression dependencies:

- `bzip2/1.0.8`
- `zlib/[>=1.2.11 <2]`

BLAS, LAPACK, GLPK, and ASL are therefore disabled explicitly.

## Recommended Handling

Freeze the core dependency graph in the recipe:

```python
self.requires("bzip2/1.0.8")
self.requires("zlib/[>=1.2.11 <2]")
tc.configure_args.append("--without-blas")
tc.configure_args.append("--without-lapack")
tc.configure_args.append("--without-glpk")
tc.configure_args.append("--without-asl")
```

Record the disabled optional features in `manifest.yaml` so downstream COIN-OR
packages can make an explicit decision later.

## Evidence

The resulting package built a static `libCoinUtils.a` and the consumer resolved
only the declared dependency graph:

```text
coinutils::coinutils
bzip2::bzip2
ZLIB::ZLIB
```

No BLAS, LAPACK, GLPK, or ASL package was mixed into this PR. The target smoke
test passed.

## Reuse Boundary

This draft supports a Path B argument because it documents dependency-boundary
discipline for the COIN-OR solver stack. It does not claim those optional
features are unusable on HarmonyOS; it says they must be adapted and validated
as separate libraries before being enabled in CoinUtils.
