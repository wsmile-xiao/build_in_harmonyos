# cpp-gsl 4.2.2 Test Report

Date: 2026-09-11

## Source verification

- Official tag: `microsoft/GSL` `v4.2.2`
- Tag commit: `152d6eb989a1ecd23fe9c9cfb2fb8cfc7c0cd0c1`
- Archive SHA-256: `59e2a0a0ea22e8bcf9db2dc4d4bd21212ac6595748295fc27a7e02cf75eac4b5`
- `ohc-run.py lang-preflight`: PASS (`task=cpp`, `detected=cpp`, CMake project with 13 C++ test sources)
- `ohc-run.py prescan --no-writeback`: PASS; CMake detected and upstream tests present

## Test inventory

The upstream `tests/` directory contains 96 `TEST(...)` declarations in 12 translation units and one standalone no-exception test program. With C++17 on Linux/OHOS, 88 GoogleTest cases are instantiated; the remaining declarations are excluded by upstream feature/compiler conditionals. The effective runtime total is therefore 89: 88 GoogleTest cases plus `gsl_noexcept_tests`.

The package consumer tests exercise `gsl::span`, `gsl::at`, `gsl::not_null`, `gsl::narrow`, `gsl::finally`, and the exported CMake target `Microsoft.GSL::GSL`.

## Test-first baseline

Before `conanfile.py` existed, the consumer command failed as required:

```text
conan test test_package cpp-gsl/4.2.2 --build=never -nr
ERROR: Package 'cpp-gsl/4.2.2' not resolved: No remote defined.
```

This confirms the consumer test cannot pass independently of the packaged library.

## Native Conan validation

Environment: WSL Linux x86_64, GCC 13.3.0, Conan 2.29.1, CMake 4.4.3, Ninja 1.13.2.

Result: PASS.

- Official source download and SHA-256 validation: PASS
- Patch application without network fallback: PASS
- Upstream CTest: 2/2 executables passed
- Upstream effective tests: 89/89 passed (88 GoogleTest + 1 no-exception)
- Conan package creation and upstream CMake install: PASS
- `test_package` configure/build/run: PASS (`cpp-gsl test_package passed`)

## HarmonyOS Conan validation

Host profile: `os=OHOS`, `os.version=6.0`, `arch=x86_64`, Clang 15, libc++, C++17. Build profile: Windows x86_64. HarmonyOS SDK: 26.0.0.

Result: PASS.

- Conan built `gtest/1.17.0` for OHOS x86_64 from its repository recipe.
- Conan built both cpp-gsl upstream test executables for OHOS.
- Conan installed all 11 GSL public headers and the upstream Microsoft.GSL CMake exports.
- Conan built `test_package` against the packaged `Microsoft.GSL::GSL` target.
- Cross execution was intentionally delegated to HDC and performed below.

## HarmonyOS PC device validation

Target: `127.0.0.1:5555`

```text
Linux localhost 5.10.210 ... x86_64
emulator 6.0.0.48(SP31DEVC00E47R1P3)
```

Result: PASS.

- Upstream `gsl_tests`: 88/88 passed on device; exit 0.
- Upstream `gsl_noexcept_tests`: exit 0.
- Conan-built consumer: `cpp-gsl test_package passed`; exit 0.
- HarmonyOS-specific test: compiled without manually defining `__OHOS__`, so its `#ifndef __OHOS__` compile guard was active; HDC runtime output:

```text
HARMONYOS_CPP_GSL_TEST_OK arch=x86_64 sum=30
```

## Repository CI

Targeted command: repository `ci/conan/build_and_test.sh` with `CI_PACKAGES=archives/c/cpp-gsl/4.2.2` and a temporary local Linux profile.

Result: PASS, 1/1 package, 100%.

- L0 recipe/package gates: PASS
- Knowledge and junk-file gates: PASS
- L1 upstream tests plus test_package: PASS
- L1e destructive negative test: PASS (removing packaged headers makes the consumer fail)
- L2 command smoke: SKIP (header-only library, no `bin/`)
- L4 patch scan: PASS
- L5 artifact probe: WARN because a header-only package has no `bin/` or `lib/`; installed `include/` was present and verified by L1e

The required `ohc-run.py finish cpp-gsl 4.2.2 built` path was also executed. Its blocking W3 local CI step passed and generated `.ci-result.json` with exit code 0 and an integrity-bound SHA-256 for `reports/w3-local-ci.log`. Non-W3 finish warnings were environment/baseline issues: its separate `conan-verify` path is hard-coded to the native aarch64 CI worker profile, the legacy submit-readiness check expects binary `packaging/` tarballs even for a Conan header-only package, and the repository knowledge graph currently has four unrelated missing fields.

The repository-wide `python3 tests/run_all.py` was also executed. Nine of eleven test modules passed. Two failures are independent of this archive and reproduce on the current baseline: `test_v1220.py` requires the CI-worker-only Git path `/data/service/hnp/git.org/git_2.45.2/bin/git`, and `test_v1221.py` reports missing baseline build-system catalog entries `headeronly` and `copy`. No framework files were changed to mask those baseline failures.
