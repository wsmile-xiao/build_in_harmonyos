# DRAFT-coinutils-upstream-noinst-test-signing

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-09
> Source: archives/c/coinutils/2.11.12

## Symptom

An autotools package can compile and package its library successfully while
the upstream `make test` path is still absent from the recipe. In COIN-OR
packages, the test executable is often declared as `noinst_PROGRAMS`, so it is
created under a recursive test directory and never enters the package.

On HarmonyOS, trying to run that unsigned executable can fail before the test
logic starts. A host-only cross build cannot be used as evidence for target
runtime either.

## Root Cause

CoinUtils defines `unitTest` in `CoinUtils/test/Makefile.am` and the root
`make test` target delegates to that directory. The target binary needs to be
built explicitly and signed before execution. The upstream test also has
optional Sample and Netlib data arguments; those inputs must be supplied
explicitly rather than silently claiming full data coverage.

## Recommended Handling

For a native OHOS build:

1. Run `make -C CoinUtils/test unitTest -j1`.
2. Remove a stale `.codesign` section with `llvm-objcopy`.
3. Sign `CoinUtils/test/unitTest` with `binary-sign-tool -selfSign 1`.
4. Run `make -C CoinUtils/test test -j1`.

For a cross build whose target executable cannot run on the build machine,
skip the runtime step explicitly and require native OHOS shadow CI before
claiming target execution.

## Evidence

The CoinUtils recipe now performs the signed upstream test sequence in its
OHOS-native build path and keeps the consumer `test_package` as a separate
link-and-run check. The manifest records the aggregate upstream target as
passed and documents that Sample/Netlib data-gated branches are not enabled
because those datasets are not vendored by this package.

## Reuse Boundary

This draft applies to C/C++ autotools libraries with recursive `test`
directories and `noinst` test executables. It does not replace the upstream
test suite, does not turn a cross-host skip into a pass, and does not claim
Sample/Netlib coverage without shipping or explicitly provisioning those
datasets.
