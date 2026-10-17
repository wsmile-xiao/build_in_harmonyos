# DRAFT-coinutils-consumer-smoke-negative-test

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

CoinUtils is a foundational library for the COIN-OR solver stack. It does not
ship a primary CLI that can prove package usability with `--version`.

A weak package test could accidentally check only that `libCoinUtils.a` exists.
That would miss broken CMake target names, missing include directories, missing
transitive link flags, and OHOS executable signing issues.

## Root Cause

The real consumer contract is C++ API usage through Conan-generated CMakeDeps:

- `find_package(coinutils REQUIRED CONFIG)`
- link `coinutils::coinutils`
- include public headers from both `include` and `include/coin`
- resolve transitive `bzip2` and `zlib`
- sign and execute the resulting ELF on OHOS

## Recommended Handling

Use a small but real API smoke:

```cpp
#include <coin/CoinPackedMatrix.hpp>

CoinPackedMatrix matrix;
if (matrix.getNumElements() != 0) {
    return 1;
}
```

The test package should sign the consumer executable before running it on OHOS.
It should also allow the repository's destructive negative test to remove the
dependency link and prove that the test genuinely depends on `coinutils`.

## Evidence

Shadow CI built and ran `coinutils_smoke` on the target worker:

```text
CoinPackedMatrix::getNumElements() = 0
OK: coinutils 2.11.12 smoke test passed.
[ok] L1e: Negative test confirmed -- test genuinely depends on coinutils
```

## Reuse Boundary

This draft is reusable for small C/C++ libraries where a minimal public API
object construction proves the package contract better than a large upstream
suite. It does not replace full upstream tests when those are available and
practical; it establishes a reliable L1 consumer floor.
