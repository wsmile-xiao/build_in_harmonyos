# abseil 20260526 validation report

Date: 2026-08-12
Package status: **pass**
Shadow runner status: **pass**

## Final results

| Check | Result | Evidence |
|-------|--------|----------|
| Source archive and checksum | pass | Official `20260526.0` archive; SHA-256 verified |
| Dependency graph | pass | Zero production Conan dependencies; `gtest/1.17.0` is test-only |
| Recipe/YAML syntax | pass | Python compile, YAML parse, Conan export, and pre-commit hook |
| Conan strict patch application | pass | Both portability patches applied during isolated `conan create` |
| OHOS compile | pass | Abseil libraries and all upstream test targets built with clang 15 |
| Upstream CTest | pass | 241/241 targets, 0 failed, 277.73 seconds |
| Consumer CTest | pass | `abseil_consumer_api` 1/1, 0 failed |
| Destructive negative test | pass | Consumer failed as required after packaged `lib/` and `include/` were removed |
| L0/L1/L4/L5 | pass | All applicable repository gates passed |
| L2 | skip | Library package has no `bin/` directory |

The package contains 93 static libraries, 216 pkg-config files, four CMake
package files, 384 headers, 24 `.inc` files, and the Apache-2.0 license.
The installed CMake and pkg-config metadata contains no `GTest::`, `gtest`, or
`gmock` reference; test helpers are excluded from the production install.

## Test portability changes

1. `absl/status/statusor_test.cc`: seven `StatusOr<std::any>` matcher
   assertions unconditionally use portable direct `ok()` assertions. This
   preserves the tested condition, avoids an OHOS libc++ `std::conjunction`
   instantiation failure in GoogleMock, and introduces no platform conditional.
   The focused `absl_statusor_test` run passed all 123 cases.
2. `absl/strings/str_format_test.cc`: the temporary-file helper unconditionally
   uses the POSIX `TMPDIR` plus `mkstemp()` mechanism. It remains portable across
   supported POSIX targets while avoiding the read-only `/tmp` on OHOS and
   introduces no platform conditional. The focused suite passed 65/65 cases.
3. `TZDIR` points to Abseil's upstream CCTZ test data so time-zone tests do not
   depend on a system zoneinfo installation. The focused time suite passed
   133/133 cases.
4. `FromChars.NaNDoubles` and `FromChars.NaNFloats` are explicitly filtered on
   OHOS. The only observed difference is the NaN payload bits produced by the
   platform conversion routine, whose payload effect is unspecified. The
   other 14 cases in `absl_charconv_test` run and pass. This filter is disclosed
   and is not counted as execution of those two internal cases.

Before these changes, an unfiltered diagnostic run had 238/241 CTest targets
passing: `absl_str_format_test`, `absl_time_test`, and `absl_charconv_test`
failed for the three platform conditions above. The final run has 241/241
CTest targets passing.

## R8 regression verification

The portability patches were revised after review to remove every platform
conditional. Verification against a fresh copy of the official `20260526.0`
archive produced these results:

```text
archive_sha256=6e1aee535473414164bf83e4ebc40240dec71a4701f8a642d906e95bea1aea0c
PATCH_CHECK=pass
R8_MACRO_MATCHES=0
TMPFILE_MATCHES=0
FDOPEN_FAILURE_CLOSE=1
```

The unconditional implementations are the same assertion and POSIX temporary
file paths exercised by the prior HarmonyOS 241/241 run. The temporary-file
helper additionally closes the descriptor if `fdopen()` fails.

## Official CI worker regression

Official CI `#22036` failed on worker `CI-040` during CMake's compiler
try-compile. Compilation succeeded, but the SDK `lld` host executable could not
load its matching `libxml2.so.16` and reported unresolved `xmlFreeDoc` and
related symbols. No Abseil source had been compiled. Build `#22015` passed the
same recipe revision on `CI-011`, confirming a worker environment difference.

The build and consumer recipes now locate `llvm/lib` from the configured OHOS
compiler and its resource directory, require the SDK's `libxml2.so.16`, and
prove that `lld -flavor gnu --version` succeeds with it before prepending the
directory inside each CMake build context. This prevents an
ambient `~/usr/local/lib` from shadowing the SDK's linker runtime without
changing the CI infrastructure or adding a target dependency. The diagnosis
and repair use knowledge entries E120/E132; E266 supplied the exact
`libxml2.so.16` plus `xmlFreeDoc` failure fingerprint. The final repair keeps
the configured SDK clang/lld pair and fails with the linker probe stderr if the
matching SDK runtime cannot be made usable.

The first repaired official run, `#22158`, completed configure and compilation
but marked all 241 tests `BAD_COMMAND`. The SDK `LD_LIBRARY_PATH` had been kept
active during CTest, leaking host linker libraries into target executable
startup. Its scope is now limited to CMake configure/build/install; upstream
CTest runs after restoration of the ambient target runtime environment.

Official run `#22206` still reported all 241 executables as `[permission
denied]`. Its generic-driver health check used bare `lld --version`, which can
return nonzero because no linker flavor was selected; this falsely activated
the GNU ld fallback. The health check now uses `lld -flavor gnu --version`, and
the fallback has been removed so test ELFs retain the SDK linker/signing path.

The repaired recipe passed official CI `#22584` and the independent rerun
`#22968`; both reported successful `conan-build-test`, consumer `test_package`,
L0, L1, and cleanup. The failure progression and final repair are captured as
Path B knowledge draft `knowledge/drafts/E321-draft-78CB.{kv,md}`. The draft
extends E120/E132 with host-environment scope and flavor-aware probing, and
records a verified conflict with E266's GNU ld fallback recommendation.

## Device environment

```text
OS: HarmonyOS 6.0, aarch64
Kernel: HongMeng 1.12.0
Compiler: clang 15.0.4
Python: 3.12.9
Conan: 2.29.1
Package: archives/a/abseil/20260526
```

## Shadow CI evidence

Final input preflight:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/7ed0ed2598ba-20260812T105429Z-preflight-46299
PREFLIGHT=pass
```

Final full run:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/7ed0ed2598ba-20260812T105503Z-run-46525
STATUS=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
```

Re-run command when the single-package device queue is free:

```sh
CI_PACKAGES="archives/a/abseil/20260526" zsh ci/conan/build_and_test.sh
```
