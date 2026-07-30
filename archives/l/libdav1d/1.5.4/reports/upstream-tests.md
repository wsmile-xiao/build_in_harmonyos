# libdav1d 1.5.4 upstream test handling

Date: 2026-07-30
Device: OHOS real device, old SSH port 56267

## Upstream test inventory

The upstream release uses Meson for test registration.

- `tests/header_test.c`: six Meson header tests for the public API headers.
- `tests/checkasm/*`: one Meson `checkasm` test if `enable_asm=true` and the
  external `checkasm` dependency is available.
- `tests/libfuzzer/*`: fuzzer binaries built by the test build, but not
  registered as Meson `test()` entries.
- `tests/dav1d-test-data`: optional decoder corpus tests behind
  `testdata_tests=true`, requiring a separate data repository.
- `tests/seek_stress.c`: optional seek stress tool behind `enable_tools=true`
  and `enable_seek_stress=true`; it is not registered as a Meson test.

## Executed on OHOS

Final Conan run dir:
`/storage/Users/currentUser/ohos-test-runs/codex-a-libdav1d-libdav1d-1.5.4-conan-oldport-r4-upstream-tests-20260730-043719-43168`

The recipe enables upstream tests for the C-only package profile and runs
`meson.test()` during `conan create`.

Result:

- `common.h_test`: pass
- `data.h_test`: pass
- `dav1d.h_test`: pass
- `headers.h_test`: pass
- `picture.h_test`: pass
- `version.h_test`: pass

Summary: 6/6 passed, 0 failed, 100% pass rate for registered tests in the
adapted C-only profile.

The same build also compiled the non-registered fuzzer binaries
`tests/libfuzzer/dav1d_fuzzer` and `tests/libfuzzer/dav1d_fuzzer_mt`.

## Not executed in this package profile

`checkasm` was identified but not executed. Upstream only registers it when
assembly is enabled and the external `checkasm` dependency is found. The
adapted Conan package intentionally uses `enable_asm=false`, and the release
archive only provides `subprojects/checkasm.wrap`, not the dependency source
itself.

`dav1d-test-data` was identified but not executed. It requires the separate
test-data repository and `testdata_tests=true`; the data corpus is not present
in the release archive used by this recipe.

`seek_stress` was identified as an optional tool, not a registered test. It
requires the dav1d CLI tool profile, while this package exports the decoder
library only.
