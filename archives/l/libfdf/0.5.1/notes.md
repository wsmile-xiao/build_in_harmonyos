# libfdf 0.5.1 HarmonyOS PC adaptation

## Status

The recipe was executed with `conan create` on an OHOS/AArch64 device. The
upstream CTest suite passed 3/3 and the explicit consumer API test passed 4/4.

## Build strategy

- Upstream build system: CMake 3.14 or newer.
- Fortran compiler: `tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")`.
- Link driver: the same `flang`, with OHOS SDK compile/link flags:
  - `--target=aarch64-unknown-linux-ohos`
  - `--sysroot=<OHOS SDK native>/sysroot`
  - `-resource-dir=<OHOS SDK clang -print-resource-dir>`
  - `-L<OHOS SDK native>/llvm/lib/aarch64-linux-ohos`
  - `-L<flang-ohos package>/lib`
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` is used for compiler checks
  because the flang-ohos package does not ship CRT objects by itself.
- No upstream source patch is applied.

## Exact upstream tests executed in build()

`build()` calls `cmake.test()`, which executes all CTest entries registered by
upstream `tests/CMakeLists.txt`:

1. `fdf-sample-test` runs `fdf-tester` in `install_tests`; the upstream pass
   regex is `Polar | Enabled`.
2. `fdf-units-test` runs `test-units` in `install_tests`; the upstream pass
   regex is `472491909`.
3. `fdf-ambiguous-units-test` runs `test-ambiguous-units` in `install_tests`;
   the upstream pass regex is `Ambiguous`.

There are exactly three upstream tests. The recipe does not replace them with
synthetic tests and does not claim a pass count before device execution.

### Contest-template test accounting

- Upstream tests: 3 CTest integration entries, 0 unit tests, 0 other tests.
- Adapted upstream tests: the same 3 CTest entries, unchanged.
- OHOS-specific test_package flow: 1 consumer flow with 4 explicit runtime
  assertions.
- Upstream test modifications: none.
- Upstream pass rate: 3/3 (100%).
- OHOS consumer pass rate: 4/4 (100%).
- OpenDesk evidence: job `20260927-045257-c41459-batch6-libfdf-ci4`.

## Package layout

- `lib/libfdf.a`
- `include/libfdf/<Flang-version>/*.mod` (including `fdf.mod` and
  `fdf_prec.mod`)
- upstream CMake package files and `lib/libfdf.pc` from `cmake.install()`
- `licenses/LICENSE` plus the upstream `share/licenses/libfdf/COPYING` install

`package_info()` scans the installed `include` tree and exposes every direct
`.mod` directory, so consumers using Conan or CMake can import `fdf` and
`fdf_prec` without hand-coding the Flang-versioned path.

## Consumer test_package

The explicit consumer test compiles a program that imports `fdf` and
`fdf_prec` from the packaged `.mod` files and links `lib/libfdf.a`. It then
performs four explicit runtime checks:

1. read `NumberOfAtoms` through `fdf_integer`;
2. convert `MeshCutoff` through `fdf_physical` and assert `1.5 Ry`;
3. read `NameOfFile` and assert its string value;
4. confirm the `new-style` marker with `fdf_defined`.

The test compiles with the same flang toolchain, links `lib/libfdf.a`, and runs
the resulting executable from a build directory containing its input FDF file.

## Verification commands

```sh
conan create archives/f/libfdf/0.5.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=libfdf/*
```

OpenDesk evidence includes the CTest summary `3/3` plus `100% tests passed`
and the consumer output `PASS: libfdf consumer API (4 checks)`.

## Remaining risk

- `flang-ohos/20.1.0` must be available in the Conan remote/cache.
- The OHOS SDK native root must contain `sysroot`, `llvm/lib`,
  `llvm/lib/aarch64-linux-ohos`, and a working `llvm/bin/clang`.
- Consumer compilation must use the same flang version because Fortran `.mod`
  files are compiler-private.
