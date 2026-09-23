# Ruckig 0.19.4 adaptation notes

## Scope

- Path: A (basic adaptation)
- Build target: C++20 `ruckig` library
- Required Conan dependencies: none
- Patches: none
- Knowledge: E092 (CMake OHOS platform mapping)
- Optional wrappers excluded: Python and Rust
- Optional remote cloud client: disabled, matching the Conan Center recipe

## Source evidence

- Upstream: https://github.com/pantor/ruckig
- Tag: `v0.19.4`
- Commit: `a8db97a4e9c55e5160a3855f739fa3b270df8e4c`
- Release date: 2026-07-15
- Archive: https://github.com/pantor/ruckig/archive/refs/tags/v0.19.4.tar.gz
- Size: 882534 bytes
- SHA256: `4f57caa350770ce162aed92285fc07ac23e83b89bf802f5f500fb4bc8b2a1905`
- License: MIT

## Build and test

The recipe uses `CMakeToolchain`, builds a shared library by default, and lets
the upstream target request C++20. The repository OHOS profile advertises
C++17, but Clang 15 supports C++20 and CMake raises the target standard through
`target_compile_features(ruckig PUBLIC cxx_std_20)`. GNU language extensions
remain enabled to match upstream CMake defaults and expose the `M_PI` constants
used by the source on strict-standard toolchains. Package metadata propagates
`_USE_MATH_DEFINES` on Windows and `_GNU_SOURCE` on Linux/OHOS so installed
public headers also compile for consumers using strict `c++20`.

The repository profile maps OHOS to `CMAKE_SYSTEM_NAME=HarmonyOS`, while current
CMake workers do not consistently ship a `Platform/HarmonyOS.cmake` module.
Following knowledge entry E092 and recent successful recipes, both the package
and consumer toolchains override only OHOS to `Linux` with processor `aarch64`.
The compiler and ABI still come from the Conan OHOS profile.

`build()` runs all upstream C++ validation used for this package:

1. `cmake.test()`
2. `test-target 5000000`
3. The six local examples invoked by upstream CI

### R51 upstream test inventory

| Step | Evidence | Result |
|---|---|---|
| Inventory | `test/` contains `test_target.cpp`, `benchmark_target.cpp`, and `randomizer.hpp`; `ctest -N` registers one `test-target` harness; doctest lists 15 cases; upstream CI runs six local examples | 3 source/support files, 1 CTest harness, 15 doctest cases, 6 examples |
| Target execution | OHOS `conan-verify` and W3 invoke CTest, `test-target 5000000`, and all six examples | 15/15 cases, 26,250,188/26,250,188 assertions, 6/6 examples |
| PR declaration | `test_package/MANIFEST.yml` and this note preserve the discovered and executed counts | 21/21 declared upstream entries, 100% |

The source contains 15 doctest cases and six subcases. The 5,000,000-trajectory
run executes 26,250,183 dynamic assertions on Windows and 26,250,188 on OHOS;
all assertions pass in both environments. No upstream test source is changed,
removed, skipped, or waived.

## Host prevalidation

Both upstream configurations, `BUILD_CLOUD_CLIENT=ON` and `OFF`, passed on a
Windows x86_64 host. Each configuration passed 15/15 doctest cases, the full
5,000,000 randomized trajectories, and 6/6 local examples. The cloud-enabled
MinGW build required host-only `ws2_32` link ordering; this is a Windows detail
and is not present in the OHOS recipe.

The authoritative raw logs are retained outside the PR under
`output/ruckig-0.19.4/evidence/`.

## Consumer and device validation

`test_package/test_main.cpp` performs 18 assertions across valid input,
offline calculation, trajectory boundary sampling, online updates, final-state
accuracy, and invalid-input rejection. `test_package/run_test.sh` is the common
Conan and HarmonyOS device entry point and preserves command, exit code, stdout,
and stderr. Passing `--self-test-failure` proves that an assertion failure and
the wrapper both return a nonzero status.

HarmonyOS PC validation passed on aarch64 with HongMeng Kernel 1.12.0, OHOS SDK
26.0.0.18, Clang 15.0.4, and Conan 2.29.1. Repository `conan-verify` passed,
W3 local CI passed 1/1 at 100%, the minimal package passed 18/18 assertions,
and its intentional negative control returned 1. The W3 log SHA256 is
`8db7bfff14c07982dc036e3d581cc684a162b6a5428fe10ab989894db67957d2`.

## Reproduction

```bash
python3 "$SKILL_ROOT/scripts/ohc-run.py" conan-verify ruckig 0.19.4
python3 "$SKILL_ROOT/scripts/ohc-run.py" finish ruckig 0.19.4 built
```
