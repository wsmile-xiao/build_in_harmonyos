# libgav1 0.20.0 upstream test report

## Scope

- Upstream: libgav1 `v0.20.0`, commit `c05bf9be660cf170d7c26bd06bb42b3322180e58`.
- Target: HarmonyOS 6.0, aarch64, Clang 15.0.4.
- Test dependencies: upstream-pinned GoogleTest `release-1.12.1` and Abseil `20220623.0`.
- Upstream source and tests: unmodified.
- Source identity: the Debian orig tarball used by `conanfile.py` is byte-identical
  to this commit's tree (387 files, 0 differences); see `source-verification.md`.
- The test tree itself is a checkout of the same commit
  (`git -C <test-tree>/src rev-parse HEAD` = `c05bf9be660cf170d7c26bd06bb42b3322180e58`).

## Test inventory and result

Upstream `tests/libgav1_tests.cmake` declares 59 test executables. Two of them are
host-conditional, so a single build can never register all 59:

| Target | Gate | Applies to |
|---|---|---|
| `common_dsp_test` | `libgav1_have_avx2 OR libgav1_have_sse4` | x86 only |
| `common_neon_test` | `libgav1_have_neon` | arm/aarch64 only |

On aarch64 the applicable inventory is therefore **58** tests, and the final
true-device run registered and executed all 58:

| Inventory | Passed | Failed | Skipped | Pass rate |
|---:|---:|---:|---:|---:|
| 58 | 58 | 0 | 0 | 100.00% |

No test was disabled or skipped by this adaptation.

### Why the first run reported 57

`cmake/libgav1_cpu_detection.cmake` enables NEON only when
`CMAKE_SYSTEM_PROCESSOR` (lowercased) matches `^arm|^aarch64`. On HarmonyOS CMake
resolved that variable to the literal string `unknown`, so `libgav1_have_neon`
was never set: `common_neon_test` was not registered (57 tests) **and the
library itself was compiled with `LIBGAV1_ENABLE_NEON=0`**, i.e. without the ARM
NEON DSP path.

`conanfile.py` now declares the target system and processor for OHOS in the
toolchain's `generic_system` block (`cmake_system_name=OHOS`,
`cmake_system_processor=aarch64`, guarded by `settings.os == "OHOS"`) — the same
workaround already used by `libmatio`, `libaec` and `libnghttp2` in this
repository. After the fix the device build defines `LIBGAV1_ENABLE_NEON=1`,
compiles 25 NEON objects (previously 0), registers `common_neon_test` as test #4
and passes 58/58.

## Reproduction

The upstream test tree must enable examples: in libgav1 0.20.0, `file_reader_test`,
`file_reader_factory_test`, and `file_writer_test` reference object targets created
by the examples configuration. `TMPDIR` must point at a writable directory: the
OHOS device mounts `/tmp` read-only, and without it `file_writer_test` fails for
environmental reasons only.

```sh
export TMPDIR=<writable-dir>
cmake -S <libgav1-source> -B <build-dir> \
  -DCMAKE_TOOLCHAIN_FILE=<ohos-conan-toolchain> \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBGAV1_ENABLE_TESTS=ON \
  -DLIBGAV1_ENABLE_EXAMPLES=ON \
  -DLIBGAV1_THREADPOOL_USE_STD_MUTEX=1
cmake --build <build-dir> -- -j8
ctest --test-dir <build-dir> -N          # Total Tests: 58
ctest --test-dir <build-dir> --output-on-failure
```

## Evidence

- Build/test tree: `…/work/upstream-tests-neon-20260927`
  (`build/` configured with the fixed Conan toolchain).
- Result: `100% tests passed, 0 tests failed out of 58`; elapsed time: 43.11 seconds; exit code `0`.
- `common_neon_test` (test #4) passed — it is the target the unfixed configuration skipped.
- `ctest-neon-58.log` SHA-256: `68b5d8e568ed86cb887512c3f2f2b598e7b70bd5b1d2647f39c8a40be89ab61f`.
- Earlier 57-test run (before the processor fix):
  `currentUser-libgav1-libgav1-0.20.0-upstream-ctest-final-20260916-114349-63965`,
  `100% tests passed, 0 tests failed out of 57`, 55.10 seconds,
  `ctest.log` SHA-256 `6b5f22f1d8dfd1f8efcc0f1b9061c64bb84f6eab3439a780aa1b81bbe931b82b`.

The initial test-only configuration with `LIBGAV1_ENABLE_EXAMPLES=OFF` failed during CMake generation because those three test targets reference absent file reader/writer objects. Enabling examples restores the upstream test configuration; this was not a source patch.
