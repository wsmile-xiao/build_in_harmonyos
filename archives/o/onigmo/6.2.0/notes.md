# onigmo 6.2.0 OHOS adaptation notes

## Current recipe

- Source: official Onigmo 6.2.0 release tarball with a pinned SHA-256.
- Build system: release Autotools files.
- Output: static `libonigmo.a`, public headers, pkg-config metadata, and `bin/onigmo-config`.
- Conan options: `--disable-shared --enable-static`.

## OHOS changes

1. `0020-config.sub-ohos.patch` accepts the `linux-ohos` system triplet.
2. `0021-config.guess-ohos.patch` detects HarmonyOS and emits the OHOS triplet.
3. `0022-configure-hmdfs-umask.patch` changes the two `config.status` temporary-directory masks from `077` to `022` for HMDFS.

No custom CMake build files, local source archives, wrapper compilers, or generated Autotools-file replacements are used by the current Conan recipe.

## Tests

- `make check` executes the upstream `testc`, `testp`, and `testcu` programs.
- `test_enc_utf8` is then built and executed directly. Upstream `make atest` pipes this program through `grep RESULT`, which can hide the program exit code.
- The Conan `test_package` links `onigmo::onigmo`, calls the public version API, and checks two semantic conditions.
- Current CI evidence: Buildbot #6793 passed for commit `fc73890a6fa01e11005a2b9de995b00c930c095c` before the latest metadata and test-exit-code corrections.

## Status

The recipe is built and tested on the OHOS aarch64 worker. It is not marked published until the PR is merged and the release pipeline uploads the package.
