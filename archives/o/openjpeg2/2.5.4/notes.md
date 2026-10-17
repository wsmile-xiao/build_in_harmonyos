# openjpeg2 2.5.4 adaptation notes

Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2043

## W0 dependency check

The packaged core `libopenjp2` library has no third-party Conan requirements.
It links only the platform math and threading libraries on Linux/OHOS. The
optional PNG, TIFF, LCMS2, and Zlib dependencies are used by the disabled codec
command-line applications, not by the core library.

A remote version-occupancy probe was attempted with:

```sh
conan download "openjpeg2/2.5.4" -r=ohpcd --only-recipe
```

The CNB remote rejected the request with `system acceleration policy not
enabled`, so the absence of a previously published recipe must be rechecked in
the shadow CI environment before publication.

## Source and build analysis

The official `v2.5.4` source archive uses CMake. Its SHA256 was independently
verified as `a695fbe19c0165f295a8531b1e4e855cd94d0875d2f88ec4b61080677e27188a`.
This recipe builds the core library with threading and disables codec tools,
JPIP, the viewer, Java bindings, documentation, LUT generators, and upstream
tests. On OHOS, the recipe enables a small portability patch that omits the
`VERSION` and `SOVERSION` target properties. This produces a directly usable
`libopenjp2.so` instead of asking CMake to create versioned symbolic links,
which HMDFS rejects. Non-OHOS builds retain the upstream versioned-library
layout.

The upstream project has two core internal test programs controlled by
`BUILD_UNIT_TESTS`: `test_sparse_array` and `bench_dwt`. The recipe builds and
runs both on OHOS/Linux. `bench_dwt` uses an explicit 256-sample reversible DWT
round trip with `-check`, so the test remains lightweight while comparing every
reconstructed sample. Both programs must return zero or the Conan build fails.

The upstream source contains 32 statically identifiable tests: 26 non-JPIP
CTest cases in `tests/CMakeLists.txt`, four registrations under `tests/unit`,
and two internal programs controlled by `BUILD_UNIT_TESTS`. The second
portability patch registers the 26
self-contained encoder, decoder, random tile access, and decode-area cases in a
standalone core test directory. This reuses the upstream test sources and
arguments without changing their assertions, while avoiding codec applications
and optional PNG, TIFF, LCMS2, and Zlib integration. Together with the two
`BUILD_UNIT_TESTS` programs, the recipe executes 28/32 upstream tests (87.5%).

Four legacy `tests/unit` registrations remain outside the gate. `testjp2`
requires the separate `openjpeg-data` repository; `testempty0/1/2` are legacy
smoke programs and are not included in the self-contained core suite.

## Consumer test

`test_package/test_openjpeg2.c` performs six checks. It verifies the exact
runtime version and default encoder parameters, encodes a 2x2 lossless grayscale
J2K image, decodes it, validates the image geometry, and compares all decoded
samples with the input.

## Local validation

Completed on Windows with CMake 4.4.2, Ninja 1.13.0, Zig/Clang 21.1.0, and
Conan 2.31.2:

- official source archive SHA256 verification passed;
- core shared-library configure and compilation passed (22 C source objects);
- install passed and produced `bin/libopenjp2.dll`, the import library, headers,
  CMake package files, and `libopenjp2.pc`;
- an isolated `conan create` completed the source, generate, build, package, and
  test_package stages with `shared=True`;
- the consumer source compiled and ran against the installed library, with 6/6
  checks passing;
- Python syntax, structured YAML parsing, recipe inspection, and diff checks
  passed.

After review of PR #5081, the recipe was extended to run 26 self-contained
upstream CTest cases plus the two core internal programs on OHOS/Linux. A local
Zig/Windows diagnostic build compiled all test targets: 23/26 CTest cases
passed, while three reversible decode-area cases stopped on Zig's signed
overflow trap. This is not reported as an OHOS result.

The official OHOS PR CI run for code commit
`e1bdd847aa7070969be1e2da5a9a00f61cba93fc` passed all 28 enabled upstream
tests: 26/26 CTest cases plus `test_sparse_array` and `bench_dwt`. The consumer
test also passed 6/6 assertions. CI gates L0, L1, L4, and L5 passed, L2 was
correctly skipped for this library-only package, and the single-package build
summary was 1/1. The run is recorded as PR CI #21599 (build #23882).

The first OHOS shadow CI run used commit
`75a2f464fb04bfb66e90467ffe3b2cd4bf6733d3`. L0 passed and all 22 core C
objects compiled, but CMake failed while creating `libopenjp2.so.7` and
`libopenjp2.so` symbolic links on HMDFS. GNU Make also reported that its
jobserver FIFO was not permitted. The recipe therefore enables the unversioned
SONAME patch and forces `tools.build:jobs=1` for both package and consumer
builds only on OHOS. The failed run is
preserved at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/75a2f464fb04-20260811T113655Z-run-14991`.

The full native Conan build passed. OHOS runtime validation remains pending
because this Windows host has no OHOS profile/toolchain. The OHPCD remote
version-occupancy query also remains blocked under the current network
acceleration policy.

## Next single-package validation

Run only this package when the real-device queue is free:

```sh
CI_PACKAGES="archives/o/openjpeg2/2.5.4" zsh ci/conan/build_and_test.sh
```

Equivalent shadow CI entry point:

```sh
/path/to/run-ohos-shadow-ci.sh archives/o/openjpeg2/2.5.4
```

Before the run, use an isolated `CONAN_HOME`, preserve the project OHOS
`settings.yml` and profiles, and set `TMPDIR=$RUN_DIR/tmp` (plus
`TMPPREFIX=$RUN_DIR/tmp/zsh` for zsh). Treat runner exit 75 as a busy lock.
