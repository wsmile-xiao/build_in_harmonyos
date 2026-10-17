# Adaptation Notes - librsync 2.3.4

## Scope

This package builds the upstream `rsync` library from the 2.3.4 release tarball.
It installs the public headers and library artifacts for downstream packages such
as `rdiff-backup`.

## Build configuration

- CMake build system
- `BUILD_RDIFF=ON`
- `ENABLE_COMPRESSION=OFF`
- `ENABLE_TRACE=OFF`
- `USE_LIBB2=OFF`
- Default package is static with PIC enabled
- Conan dependency: `popt/1.16`
- Conan tool requirement: `perl/5.42.2`

`BUILD_RDIFF` is enabled because `popt/1.16` is now published in the `ohpcd`
Conan registry for the OHOS/aarch64 profile used by this package. The
repository tree still has an older partial `archives/p/popt/1.16` archive, but
the build resolves `popt/1.16#cca44e0c65c2ff043d329f27a068a956` from the remote
Conan registry rather than from that source-tree archive. See
`reports/dependency-resolution.md` for the `conan download "popt/1.16"
-r=ohpcd --only-recipe` evidence.

The optional `Mutate` script test needs Perl, so the recipe consumes the
published `perl/5.42.2` package as a build/test tool requirement and runs CTest
in the Conan build environment.

## Upstream tests

The release source registers seven library CTest cases that do not require
`popt`:

- `isprefix_test`
- `netint_test`
- `rollsum_test`
- `rabinkarp_test`
- `hashtable_test`
- `checksum_test`
- `sumset_test`

The recipe runs `ctest --output-on-failure` during `build()` when tests are
executable in the current Conan build context.

Upstream also defines eight optional `rdiff` CLI script tests. With
`BUILD_RDIFF=ON`, all eight are registered. The `Mutate` test is executed with
the Conan-provided `perl/5.42.2` environment; all eight `rdiff` tests pass.

## Consumer test

`test_package` uses `find_package(librsync)` and links a C executable against
`librsync::librsync`. The executable validates:

- `rs_librsync_version` reports the packaged 2.3.4 version
- `rs_sig_args` returns a valid signature argument set for a sample file size
- the selected signature magic, block length, and strong checksum length are
  usable non-zero values

## Verification

- Local static checks: `py_compile` and `git diff --check` passed.
- OHOS PC runner run on port 33332:
  `ci/conan/build_and_test.sh archives/l/librsync/2.3.4` passed on 2026-08-04.
- CI gates: L0 pass, L1 pass, L2 pass (`rdiff --version`), L4 pass, L5 pass.
- Upstream CTest: 15 registered, 15 passed, 0 skipped.
- Conan `test_package`: 1/1 CTest passed, then the consumer executable was run
  directly and printed `librsync librsync 2.3.4 ok`.
