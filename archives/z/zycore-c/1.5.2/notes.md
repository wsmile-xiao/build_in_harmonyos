# zycore-c 1.5.2 adaptation notes

## Scope

- Issue: TBD. No `zycore-c` issue identifier was found in the repository or supplied session context. Per the current task direction, the missing issue does not block this PR and must be supplemented later.
- Branch: `feat/zycore-c-1.5.2`
- Package: `zycore-c/1.5.2`

## W0 dependency check

The upstream CMake project links no third-party libraries. Its only optional test dependency is GoogleTest: enabling `ZYCORE_BUILD_TESTS` finds a system GTest or downloads it during configuration. The package recipe disables upstream tests to keep source and build stages offline and adds no Conan requirements. No dependency adaptation needs to be split out.

## Source and build analysis

- Official source: `https://codeload.github.com/zyantific/zycore-c/tar.gz/refs/tags/v1.5.2`
- SHA-256: `943f91eb9ab2a8cc01ab9f8b785e769a273502071e0ee8011cdfcaad93947cec`
- License: MIT.
- Upstream provides CMake and Meson; this recipe uses CMake because it exports and installs the `Zycore::Zycore` CMake target directly.
- `ZYCORE_BUILD_SHARED_LIB`, `ZYCORE_BUILD_EXAMPLES`, and `ZYCORE_BUILD_TESTS` are explicit. The default package is static, matching upstream's default. Doxygen discovery is disabled to avoid an incidental documentation build.
- The upstream CMake test suite has three GoogleTest executables: `String`, `Vector`, and `ArgParse`. It is kept out of the package recipe because it downloads or locates GoogleTest during configuration; it was validated separately on the device with the upstream-pinned GoogleTest revision.

## Consumer test

`test_package/test.c` links the installed `Zycore::Zycore` target and exercises allocator-backed `ZyanVector` initialization, insertion, size retrieval, indexed value retrieval, and destruction. This is an API and runtime assertion, not an include-only smoke test.

## Local verification and handoff

The official archive was downloaded locally and its SHA-256 matches `conandata.yml`.

On 2026-09-14, all upstream C sources were compiled into a static `Zycore.lib` with MSVC 2022. The consumer was then compiled separately, linked to that archive, and run using the same `ZYCORE_STATIC_BUILD` public definition that the upstream CMake target exports for a static library. It passed:

```text
zycore-c vector consumer test passed
```

`conan inspect` and `conan export ... --user=ohpcd --channel=stable` also passed. This workstation has no `cmake`, `ninja`, or OHOS compiler on `PATH`, so a local `conan create` / CMake package-install validation was not attempted. Do not run a broad repository scan.

The first isolated true-device run reached Conan source retrieval and verified the archive download, but Conan selected ZIP extraction because the codeload URL has no filename suffix. `conandata.yml` therefore pins `filename: zycore-c-1.5.2.tar.gz`; the next single-package runner submission validates the corrected extraction path.

```sh
CI_PACKAGES="archives/z/zycore-c/1.5.2" zsh ci/conan/build_and_test.sh
```

For the single-package shadow runner when the device queue is free:

```sh
/path/to/run-ohos-shadow-ci.sh archives/z/zycore-c/1.5.2
```

Before the first true-device run, use an isolated runner/CONAN_HOME, copy the project `settings.yml`, set `TMPDIR="$RUN_DIR/tmp"` and `TMPPREFIX="$RUN_DIR/tmp/zsh"`, and inspect the generated runner logs rather than relying on stdout.

Potential OHOS follow-up: upstream adds `Threads::Threads` only when `CMAKE_SYSTEM_NAME` is `Linux`; the recipe exposes `pthread` as an OHOS system library for downstream static linking. Confirm that the true-device build and consumer link retain this transitive requirement.

## True-device validation

An isolated OHOS/aarch64 Conan job completed on 2026-09-14 with runner exit code `0`.

- Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-zycore-c-zycore-c-1.5.2-20260914-conan-filename-20260914-183803-27721`
- Profile: `ohos-aarch64`, Conan 2.29.1.
- Package artifact: `lib/libZycore.a` (60058 bytes), plus 22 public headers and five CMake package files.
- Consumer output: `zycore-c vector consumer test passed`.
- Gate results: L0 pass, L1 pass, L2 skip (pure library, no `bin/`), L4 pass (no patches), L5 pass.
- Single-package summary: `Total: 1`, `Success: 1`, `Failed: 0`.

The first device attempt established that a codeload URL without a filename extension makes Conan select ZIP extraction. It failed before compilation; the explicit tarball `filename` in `conandata.yml` fixed that issue in the successful retry.

## Upstream GoogleTest validation

The upstream test suite was executed separately on the same isolated OHOS/aarch64 job after building the GoogleTest commit pinned by upstream (`ee3aa831172090fd5442820f215cb04ab6062756`). This test-only setup supplies GTest through `CMAKE_PREFIX_PATH`; it does not alter the shipped recipe or upstream test sources.

- Runner directory: `/storage/Users/currentUser/ohos-test-runs/codex-zycore-c-zycore-c-1.5.2-20260914-upstream-gtest-werror-20260914-185709-39692`
- CTest targets: `String`, `Vector`, and `ArgParse`; all 3/3 passed.
- GoogleTest cases: 31/31 passed, counted from `--gtest_list_tests` for the three upstream executables.
- Runner exit code: `0`.

The current CMake version required `CMAKE_POLICY_VERSION_MINIMUM=3.5` for the old upstream-pinned GoogleTest CMake file. The HarmonyOS clang wrapper also forwards link-only flags during C++ compilation; the test-only GoogleTest build used `-Wno-error=unused-command-line-argument` because GoogleTest otherwise promotes that wrapper warning to an error. These settings are validation harness compatibility only and are not shipped in the recipe.
