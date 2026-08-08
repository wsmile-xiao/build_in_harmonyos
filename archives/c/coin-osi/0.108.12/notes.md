# coin-osi 0.108.12

## Scope

This recipe ports COIN-OR Osi 0.108.12 for OpenHarmony PC aarch64.
It is the full Osi package path and depends on `coin-utils/2.11.13`,
which is provided by PR #3882.

## Changes

- Keep the recipe, source metadata, patches, and test package together under
  `archives/c/coin-osi/0.108.12/`.
- Remove the temporary no-CoinUtils patch and restore the real CoinUtils
  dependency.
- Keep portability patches for install-time pkg-config and HarmonyOS detection.
- Add official COIN-OR Data-Sample 1.2.13 as test-only input for the upstream
  `unitTest` executable.
- Smoke-test the package through `coin-osi::libosi`, including transitive
  CoinUtils headers and symbols.

## Validation

- `python -m py_compile conanfile.py test_package/conanfile.py`
- Patch metadata is static-checked for matching patch files and `strip` values.
- Upstream test suite handling:
  - Osi 0.108.12 ships a real upstream test target: `Osi/Makefile.am` defines
    `test`, which enters `Osi/test`, builds the single `unitTest` executable,
    and runs `./unitTest $(unittestflags)`.
  - The recipe now builds `Osi/test/unitTest`, signs it on native OHOS, and
    runs `make -C Osi/test test` with an explicit `-mpsDir` pointing at the
    unpacked official Data-Sample archive during `conan create` when the
    target executable can run on the build host.
  - The optional CPLEX, GLPK, Gurobi, Mosek, SoPlex, and XPRESS test sources
    are guarded by `COIN_HAS_*` conditionals in `Osi/test/Makefile.am`. This
    recipe explicitly configures those solver backends off because the solvers
    are either proprietary or outside the PR #3877 dependency closure.
  - Sample MPS input is supplied from official Data-Sample so the default
    OsiRowCut/OsiColCut/OsiCuts checks do not fall back to the missing
    `../../Data/Sample` path. Netlib coverage still requires `COIN_HAS_NETLIB`
    and a Netlib data package; it remains outside this PR because the default
    Vol-derived `OsiTestSolver` path explicitly skips Netlib.
- The latest physical OpenHarmony PC run built and installed `libOsi.a` and
  `libOsiCommonTests.a`, then compiled, signed, and executed both the upstream
  `unitTest` and the `osi_smoke` consumer successfully. The upstream test ended
  with `All tests completed successfully`, and the consumer printed
  `OK: coin-osi 0.108.12 smoke passed`.
- The repository CI helper completed with L0, L1, L4, and L5 passing. L2 skipped
  because this library package does not install a `bin/` directory; runtime
  coverage is provided by the signed upstream and consumer tests executed by
  `conan create`.

The metadata remains `draft` until repository CI completes, following the
merged #3519 status convention.
