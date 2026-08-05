# Blitz++ 1.0.2 adaptation notes

## Package model

The recipe builds Blitz++ with upstream CMake and packages the generated headers
plus `libblitz.a`. Dynamic libraries are disabled for the package build so OHOS
does not receive unsigned shared objects.

## Upstream validation

`BUILD_TESTING=ON` is enabled and the upstream `testsuite` target is built. The
recipe then runs CTest for the official testsuite entries when target binaries
can execute on the build machine.

Local Windows/MinGW validation passed on 2026-08-05 with Conan using the
`win-mingw` profile: CTest reported `100% tests passed, 0 tests failed out of
57`, and `test_package` reported all 4 consumer assertions passed.

## OpenHarmony validation

OpenHarmony PC aarch64 validation passed on 2026-08-05 through the new SSH port
33332. The successful runner directory was:

`/storage/Users/currentUser/ohos-test-runs/codex-a-1.0.2-blitz-1.0.2-newport-r1-conan-20260805-183407-41802`

The full package reference was:

`blitz/1.0.2#7d9d43467a56fc549514c2fe35c5bdcb:6b129b068851896169fae42d399fa922d239ce8a#e2f42d1780c36120e962991691fad5bb`

Remote results:

- Upstream tests: CTest `100% tests passed, 0 tests failed out of 57`
- Consumer test: `test_blitz` all 4 assertions passed
- Gates: L0 pass, L1 pass, L2 skip (`no bin/ dir`), L4 pass, L5 pass
