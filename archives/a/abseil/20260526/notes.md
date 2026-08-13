# abseil 20260526 HarmonyOS adaptation notes

## Scope

- Issue: 2073
- Branch: `feat/abseil-20260526-2073`
- Archive/Conan version: `20260526`
- Official upstream tag: `20260526.0`
- Build system: CMake
- Package type: static C++ component library

The issue version omits the upstream patch suffix. `conandata.yml` maps the
required Conan version to the official `20260526.0` release archive.

## Dependency result

The production package has no third-party Conan dependencies. It requires
C++17 and platform Threads. The upstream tests use the separately published
`gtest/1.17.0` package through `test_requires`, so GoogleTest is not propagated
to Abseil consumers.

## Recipe design

1. Build static position-independent libraries with C++17.
2. Enable all upstream CTest targets and resolve the published external
   GoogleTest CMake package.
3. Preserve upstream `lib/cmake/absl/abslConfig.cmake` and the complete
   `absl::*` component target graph instead of replacing it with a generated
   aggregate target.
4. After executing tests, regenerate the install rules with testing disabled
   so test helper targets and GoogleTest references do not leak into the
   production package.
5. Package the Apache-2.0 license explicitly.
6. Set `TZDIR` to upstream CCTZ test data and use the CI-provided writable
   `TMPDIR` for OHOS test runtime portability.
7. Keep the package library-only; no `commands.json` is needed.

## Compatibility boundary

Two patches modify test sources only:

- `0001-statusor-any-ohos-libcxx-test.patch` unconditionally replaces seven
  GoogleMock matcher expressions for `StatusOr<std::any>` with semantically
  equivalent, portable direct `ok()` assertions. This avoids an OHOS libc++
  template instantiation failure without platform conditionals or library-code
  changes.
- `0002-ohos-test-runtime-portability.patch` makes the str-format test temporary
  file unconditionally use the POSIX `TMPDIR`/`mkstemp()` mechanism. This works
  across supported POSIX targets and avoids read-only `/tmp` on OHOS without a
  platform conditional.

The recipe filters exactly `FromChars.NaNDoubles` and
`FromChars.NaNFloats` on OHOS. Their only mismatch is the NaN payload bit
pattern returned by the platform conversion routine; the payload effect is
unspecified. All other cases in the binary run. The filter is recorded in the
manifest and validation report and is not presented as execution of those two
internal cases.

## Validation

Local/front-loaded checks:

- Official source URL and SHA-256 verified.
- Upstream CMake, dependencies, and 241-test inventory inspected.
- Recipe Python syntax, YAML semantics, Conan export/graph, and repository
  pre-commit hook passed.
- `gtest/1.17.0` recipe and OHOS armv8 binary availability verified on
  `ohpcd`.

HarmonyOS 6.0 aarch64 shadow CI:

- Input preflight passed for commit `7ed0ed2598ba22ec64156e781015da9079c7e54f`.
- Both patches applied through Conan's strict patch parser.
- Upstream CTest passed 241/241 targets in 277.73 seconds.
- Consumer CTest passed 1/1 and exercised eight assertions over version,
  `flat_hash_map`, `StatusOr`, and `StrCat` APIs.
- L0, L1, L4, and L5 passed; L2 skipped correctly for a library package.
- The destructive R34 negative test passed.
- Runner status: `pass` (`setup_rc=0`, `build_rc=0`).

## Official CI linker regression

Official CI build `#22036` on worker `OpenHarmonyPCDeveloper-CI-040` failed
before any Abseil source was compiled. CMake's compiler probe compiled its test
object, but the OHOS SDK `lld` process could not start because the ambient
`LD_LIBRARY_PATH` selected a missing or ABI-incompatible `libxml2.so.16`.
The resulting unresolved `xmlFreeDoc` and related symbols belong to the host
linker process, not to Abseil or a target-side package dependency. The same
recipe revision passed build `#22015` on worker `CI-011`, which isolated the
failure to worker host-library ordering.

The recipe now derives the active SDK `llvm/lib` directory from Conan's actual
compiler executable and `clang -print-resource-dir`, verifies that it contains
`libxml2.so.16`, and verifies `lld -flavor gnu --version` with that directory
prepended before using the linker. The directory is prepended only inside the
build/package environment.
The consumer `test_package` applies the same guard in its separate Conan
process. This avoids a hard-coded SDK version and covers CMake configure,
build, the upstream suite, the install-rule regeneration, and consumer link.
The probe invokes the generic driver as `lld -flavor gnu --version`; a bare
`lld --version` is not a valid health check because the driver may require an
explicit linker flavor. If the SDK runtime is genuinely unusable, the recipe
fails with the probe stderr instead of silently changing linker semantics.

Official CI `#22158` proved that the linker repair passed configure and the
complete build, but initially reported all 241 tests as `BAD_COMMAND`. The
cause was an overly broad environment scope: the SDK host-library path also
wrapped `cmake.test()`, so target executables inherited host linker libraries.
The final scope covers configure/build only; CTest runs after that environment
is restored, with only `TZDIR`, `GTEST_FILTER`, and CTest diagnostics applied.

Official CI `#22206` confirmed the remaining failure was not library loading:
all 241 test binaries were built, but CTest could not start them and reported
`[permission denied]`. The bare `lld --version` health check had incorrectly
selected the GNU linker fallback even when the SDK `lld` was usable with its
GNU flavor. That fallback changed the generated ELF/signing behavior. It has
been removed; the recipe always uses the configured SDK clang/lld pair after
the flavor-aware probe succeeds.

Evidence:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/7ed0ed2598ba-20260812T105429Z-preflight-46299
/storage/Users/currentUser/ohpc-ci-shadow/runs/7ed0ed2598ba-20260812T105503Z-run-46525
```

## Knowledge base usage

This adaptation used knowledge entry E096 for Abseil's OHOS C++17/CMake
configuration and component-package guidance. The official CI regression
matched E120/E132 for the SDK `lld` host-library path and E266's exact
`libxml2.so.16`/`xmlFreeDoc` failure signature. The common adaptation and first
device-start guide was also used for isolated `CONAN_HOME`, writable `TMPDIR`,
single-package device locking, shadow input hashes, and evidence collection.

Path B draft `knowledge/drafts/E321-draft-78CB.{kv,md}` records the new,
reusable boundary discovered by this adaptation. It does not duplicate the
initial `libxml2` diagnosis: it documents why a bare generic-driver probe can
falsely trigger E266's GNU ld recommendation, why that fallback produces target
ELFs rejected with `permission denied`, and why the SDK host-library environment
must end before CTest. The draft relates to E120/E132 and explicitly conflicts
with E266's linker fallback.

## Re-run commands

When the device queue is free:

```sh
CI_PACKAGES="archives/a/abseil/20260526" zsh ci/conan/build_and_test.sh
```

Direct diagnosis:

```sh
conan create archives/a/abseil/20260526 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 最终状态

The recipe-level linker runtime repair and static checks are complete. Official
CI `#22584` and the independent rerun `#22968` both passed with the SDK
clang/lld pair, all 241 upstream CTest targets, the consumer test package, L0,
and L1. The previously recorded full shadow run also remains 241/241 upstream
targets plus 1/1 consumer test passed.
