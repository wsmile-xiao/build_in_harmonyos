# DRAFT-coinutils-ohos-tool-requirements-leak

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

An early shadow CI run failed in L0 dependency resolution before exercising
CoinUtils itself. The failing requirements were copied Windows/MSVC helpers:

- `automake/1.16.5`
- `msys2/cci.latest`

The target package was an OpenHarmony autotools build using the generated
release `configure` scripts. It did not run autoreconf and did not need MSYS.

## Root Cause

Porting from a general Conan Center recipe can accidentally preserve tool
requirements that belong to another platform branch. On OHOS, those tools widen
the graph and can fail registry resolution. That is a dependency-boundary issue,
not evidence that the target library itself is blocked.

## Recommended Handling

Before shadow CI, classify every `tool_requires` entry:

- Is it executed in the OHOS path?
- Is it needed because upstream generated files are missing?
- Is it a separate tool adaptation that should have its own package?

For CoinUtils 2.11.12, the correct action was to remove the copied
`build_requirements()` block that only added MSVC/MSYS tools. The actual OHOS
build path uses:

- generated `configure` scripts from the release tarball
- versioned patches for generated files
- `/system/bin/sh` or an available build shell
- the existing OHOS Conan profile

## Evidence

After removing the unrelated tool requirements, shadow CI passed:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
Pass rate: 100.0% (1/1)
```

## Reuse Boundary

This draft does not say that `automake` is never needed. It says not to carry
platform-specific tool requirements into a target-only package when the adapted
path uses generated release files. If a future COIN-OR version requires
autoreconf, that toolchain work should be split out and validated separately.
