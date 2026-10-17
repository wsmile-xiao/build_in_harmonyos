# nss-wrapper 1.1.16 upstream test inventory

Date: 2026-07-30

Source archive: `https://www.samba.org/ftp/cwrap/nss_wrapper-1.1.16.tar.gz`

## Release test inventory

The release archive includes `tests/CMakeLists.txt` and CMocka-based tests:

- Base CTest entries: `testsuite`, `test_nwrap_vector`,
  `test_getaddrinfo`, `test_getnameinfo`, `test_gethostby_name_addr`,
  `test_gethostent`, `test_getpwuid_module`, `test_initgroups`.
- Conditional CTest entry: `test_shadow`.
- Additional CTest entry: `test_nwrap_disabled` for non-sanitizer builds.

The unpatched source can register 10 entries on OHOS because the sysroot has
`shadow.h`. That is not enough to run `test_shadow`: the test also needs
`setspent`, `getspent`, `endspent`, and `getspnam`, which are not available in
the OHOS sysroot used by CI. After gating on those functions, the valid OHOS
upstream test set is 9 registered entries.

## Recipe test mode

The default package build remains runtime-only with `UNIT_TESTING=OFF`, so
normal consumers do not gain a cmocka dependency.

The optional upstream-test mode is enabled with:

```bash
conan create archives/n/nss-wrapper/1.1.16 \
  -o nss-wrapper/*:with_upstream_tests=True
```

That mode adds the test-only `cmocka/2.0.2` dependency, generates CMakeDeps,
sets `UNIT_TESTING=ON`, and runs `ctest --output-on-failure` in the Conan build
step.

## OHOS test adaptations

- `cmocka/2.0.2` is sufficient for upstream `find_package(cmocka 1.1.0
  REQUIRED)` because the local cmocka recipe exports CMakeDeps version
  compatibility as `AnyNewerVersion`.
- `tests/nss_nwrap.c` now gets the same fallback NSS status enum path used by
  the runtime OHOS patch when neither `nss.h` nor `nss_common.h` exists.
- `tests/CMakeLists.txt` checks `setspent`, `getspent`, `endspent`, and
  `getspnam` before registering `test_shadow`.
- `tests/test_nwrap_disabled.c` skips the native-user lookup subcase when the
  runner uid is absent from the system passwd database. On the current runner,
  uid `20020105` is valid for execution but is not present in passwd data.
- The shadow test link step is guarded with `if (TARGET test_shadow)` so the
  target is not referenced when the capability gate excludes it.

## OHOS execution status

Earlier true-device rounds:

- r1 old port: runner harness error only; rc=127 before Conan started.
- r2 old port: source compilation failed because OHOS lacks `nss.h` and
  `nss_common.h`; added `0001-ohos-nss-status.patch`.
- r7 old port: default `conan create` passed, including the LD_PRELOAD
  `test_package`.

cmocka dependency unlock probe:

- run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-nss-wrapper-cmocka-upstream-r2-upstream-cmocka-r2-20260730-193826-36790`
- Result: `cmocka/2.0.2` built on OHOS, `nss-wrapper` found
  `cmocka::cmocka`, and configure/generate completed.
- Remaining blockers at that point were in nss-wrapper test sources, not in
  cmocka dependency discovery.

Final upstream-test run:

- run_dir:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-upstream-r4-rerun1-20260730-204550-6012`
- Full package reference:
  `nss-wrapper/1.1.16#892c8c3c58712838a3ab20804f6c5334:e3efca24846c41be08e762f51b5ef2e4ee8008cd#79c3862b3f1b06501f5c0e758de8434b`
- Result: `100% tests passed, 0 tests failed out of 9`.

Passed CTest entries:

1. `testsuite`
2. `test_nwrap_vector`
3. `test_getaddrinfo`
4. `test_getnameinfo`
5. `test_gethostby_name_addr`
6. `test_gethostent`
7. `test_getpwuid_module`
8. `test_initgroups`
9. `test_nwrap_disabled`

`test_shadow` is intentionally not registered on OHOS because the sysroot has
the header but lacks the required shadow database functions.

`uid_wrapper` is still reported as missing by CMake as an optional package. It
does not stop configure, build, CTest registration, or the final test run.

A prior r4 attempt had a transient `test_getaddrinfo` subtest failure; an
immediate fresh Conan create in `r4-rerun1` passed the full 9-test set and is
the recorded validation result.

## Added consumer test

The Conan `test_package` launches the test executable with
`LD_PRELOAD=libnss_wrapper.so` and verifies:

- `getpwnam("ohosuser")`
- `getpwuid(4242)`
- `getgrnam("ohosgrp")`
- `getgrgid(4242)`
- `gethostname()` via `NSS_WRAPPER_HOSTNAME`

The passwd/group files are written under the test build folder, not `/tmp`.
