# icu4c 77 adaptation notes

## Scope

- Package: icu4c/77
- Upstream release: ICU 77.1
- Issue: #807
- Source: https://github.com/unicode-org/icu/releases/download/release-77-1/icu4c-77_1-src.tgz

## Adaptation

- Added a Conan Autotools recipe.
- Configures from the upstream `source/` directory.
- Builds static libraries and packages ICU data statically with `--with-data-packaging=static`.
- Rejects `shared=True`, so the package cannot create shared libraries that
  collide with the ICU libraries supplied by OpenHarmony.
- Enables the upstream test suites and runs `make check`.
- Declares both Autotools build and host as `aarch64-unknown-linux-ohos`
  because the competition worker builds and runs natively on OHOS armv8.
- Keeping build and host identical prevents ICU from entering cross-compilation
  mode and requiring an external `--with-cross-build` tool tree.
- Runs the out-of-tree Autotools build under `$HOME/tmp`, where Autoconf can
  create its private temporary directories without changing the generated
  `configure` script.
- Disables samples, extras, layout, and layoutex to keep the package scope focused.

## Tests

- Runs the upstream `testdata`, `intltest`, `cintltst`, and `iotest` suites
  through `make check`.
- Added a CMake-based `test_package` that compiles, links, and runs a consumer
  against the packaged ICU libraries.
- The consumer verifies UTF-8 conversion, collation, case conversion, and the
  packaged ICU version.

## Local Validation

- Linux x86_64 Release `conan create` completed successfully.
- Upstream `make check -j1` passed all 4 registered suites:
  `testdata`, `intltest`, `iotest`, and `cintltst`.
- The added consumer test passed 1/1 with 7 checks.
- `git diff --check` passed.
- The official source archive SHA256 was verified locally.
- This local result is a native Linux preflight; official OHOS/aarch64 status
  remains determined by the competition CI.
- CI builds #10728 and #10745 exposed a false cross-compilation classification
  caused by different GNU build and OHOS host triplets; the recipe now uses the
  worker's native OHOS triplet for both values.
- CI build #11217 reached the upstream `cintltst` suite on OHOS but aborted in
  `ucptrietest/TrieTestSet1` when the golden-data helper used `tmpfile()`
  without checking for a null stream. Added a focused upstream-test portability
  patch that falls back to the recipe's writable `TMPDIR`, so the golden
  comparison still runs instead of being skipped.
