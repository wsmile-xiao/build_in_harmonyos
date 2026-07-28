# libjodycode 4.1.2 adaptation notes

## Status

- Branch: `feat/libjodycode-4.1.2`
- Issue: `#1410`
- Current phase: device runner validation passed for the default shared package and an additional static-package smoke; PR CI re-run is pending after adding source mirrors for Codeberg 429 fallback
- Package path: `archives/l/libjodycode/4.1.2/`

## W0 Dependency Check

libjodycode is a small C utility library with no external Conan dependencies. It only needs the system C library plus basic build tools such as Makefile tooling, `gzip`, `install`, `ln`, and `rm`.

I attempted to check remote version occupancy with:

```sh
conan download libjodycode/4.1.2 -r=ohpcd --only-recipe
```

Remote check on 2026-07-25 used isolated `CONAN_HOME` directories. The same `ohpcd` remote successfully listed `zlib/1.3.1`, so the remote itself was reachable. `conan list 'libjodycode/4.1.2#*' -r=ohpcd` returned `not found`; `conan download libjodycode/4.1.2 -r=ohpcd --only-recipe` returned `error:system acceleration policy not enabled`. Treat the `conan list` result as evidence that `libjodycode/4.1.2` is not currently published, but recheck from the final device/CI environment before PR submission.

The ohpcd check was repeated after issue `#1410` was confirmed. The isolated remote still listed `zlib/1.3.1` and still returned `not found` for `libjodycode/4.1.2`.

The successful device runner log later repeated the CI L0j registry collision check and reported `version not in registry yet (first publish)`.

## Source

- URL: `https://codeberg.org/jbruchon/libjodycode/archive/v4.1.2.tar.gz`
- sha256: `0343cf2ff53fb19887663b8c1f47210fc2d1599a4a8f95e292991d5b1034bc05`
- Verified fallback URLs for CI source-server rate limiting:
  - `https://deb.debian.org/debian/pool/main/libj/libjodycode/libjodycode_4.1.2.orig.tar.gz`
  - `https://sources.voidlinux.org/libjodycode-4.1.2/v4.1.2.tar.gz`
- Fallback tarball sha256: `a7085da591e0c314eb3442e7b258a6b6944e6978ecb2764ab33f3cb840f47ff4`
- Extracted root: `libjodycode/`
- Upstream macros: `LIBJODYCODE_VER "4.1.2"`, `LIBJODYCODE_VERDATE "2026-02-08"`

This round successfully downloaded the real 4.1.2 tarball from Codeberg and does not reuse the old note's 4.0 GitHub mirror source.

The source was rechecked on 2026-07-25:

- Downloaded `v4.1.2.tar.gz` from Codeberg.
- SHA256 matched `0343cf2ff53fb19887663b8c1f47210fc2d1599a4a8f95e292991d5b1034bc05`.
- `libjodycode.h` declares `LIBJODYCODE_VER "4.1.2"` and `LIBJODYCODE_VERDATE "2026-02-08"`.

PR CI build #10211 later failed in `conan-build-test` because Codeberg returned HTTP 429 while downloading the primary source tarball. On 2026-07-26, Debian and Void Linux fallback tarballs were downloaded locally. Their compressed tarball SHA256 is `a7085da591e0c314eb3442e7b258a6b6944e6978ecb2764ab33f3cb840f47ff4`; after extraction, both fallback archives matched the Codeberg archive exactly by per-file SHA256 across 66 files. The recipe now keeps Codeberg as the primary source and falls back to those verified same-version mirrors only if the primary source fails.

## Build System

- Pure Makefile project.
- No `configure`, `CMakeLists.txt`, or `meson.build`.
- Default target builds `manual sharedlib staticlib`.
- Non-x86_64 or cross-compiler detection automatically defines `NO_SIMD`, `NO_SSE2`, and `NO_AVX2`.
- Install uses `PREFIX` and `DESTDIR`.

The Conan recipe obtains `CC`, `AR`, and `RANLIB` from `tools.build:compiler_executables`, uses `-j1`, and passes `SHELL` from `CONFIG_SHELL` or the OHOS bash fallback to avoid relying on an unavailable default `/bin/sh`.

Shared/static review: upstream builds and installs both `libjodycode.so.*` and `libjodycode.a`. This is not a system same-name library, so shared output is not stripped by R26. `package_info()` exposes linker name `jodycode`, and the CMake target is explicitly set to `libjodycode::libjodycode`. Device runner validation confirmed the default shared package publishes `libjodycode.so.4.1.2`, `libjodycode.so.4`, and `libjodycode.so`; the additional static run with `shared=False` publishes `libjodycode.a` only.

## Tests

Upstream `make test` only runs `test.sh`, which is a dummy script that prints `OK`. The recipe keeps the upstream test trace; on OHOS it invokes `test.sh` through the resolved bash because the default shell path is unreliable. A real consumer API test in `test_package` covers downstream linking and runtime behavior.

Consumer test coverage:

- Version and API feature metadata.
- `jc_streq`, `jc_strneq`, `jc_strcaseeq`.
- `jc_numeric_strcmp`.
- `jc_collapse_dotdot`.
- `jc_strtoepoch`.
- `jc_size_suffix`.
- `jc_get_errname`, `jc_get_errdesc`.
- Deterministic `jc_block_hash`.

## Local Verification

- Downloaded official source and confirmed sha256.
- Extracted and inspected source tree and Makefile.
- Confirmed local Conan version is 2.29.1.
- `python -m py_compile` passed for the recipe and test_package.
- YAML parse passed for `manifest.yaml`, `conandata.yml`, and `test_package/MANIFEST.yml`.
- `conan inspect` and `conan export libjodycode/4.1.2@ohpcd/stable` passed with isolated `CONAN_HOME`.
- After adding source mirrors, `conan source` passed in an isolated temporary directory and confirmed `LIBJODYCODE_VER "4.1.2"` / `LIBJODYCODE_VERDATE "2026-02-08"`.
- `git diff --check` passed; Git only warned that LF files may be converted to CRLF on checkout.
- Windows host lacks `make` and `cmake`, so `conan create` was not run locally.
- Device runner validation was started only after the user confirmed the true device was idle. The job used isolated `CONAN_HOME` and the runner global lock.

## Device Verification

Before validation, the true-device lock and load were checked:

- Global lock directory: free.
- No residual `conan`, `cmake`, `ninja`, `make`, `ctest`, `apache`, or `arrow` processes were observed.
- Isolated job base: `/storage/Users/currentUser/ohos-users/codex-libjodycode/libjodycode-4.1.2-1410-20260725-071503`
- Isolated `CONAN_HOME`: `/storage/Users/currentUser/ohos-users/codex-libjodycode/libjodycode-4.1.2-1410-20260725-071503/conan-home`

Default shared validation:

- Command: `sh "$OHOS_JOB_BASE/run-conan-heavy.sh"`
- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-libjodycode-4.1.2-libjodycode-4.1.2-1410-20260725-071503-conan-20260725-073958-31145`
- Result: pass, exit code 0.
- Evidence: `conan create` passed; CMakeDeps declared `libjodycode::libjodycode`; package contained `libjodycode.so.4.1.2`, `libjodycode.so.4`, `libjodycode.so`, header, and manpage; `test_package` built and ran `libjodycode 4.1.2 consumer API test: OK`; CI negative test confirmed the test genuinely depends on the package artifacts.

Static option validation:

- Command: `noglob conan create "$CI_REPO_ROOT/archives/l/libjodycode/4.1.2" -pr:h="$CI_REPO_ROOT/ci/conan/profiles/ohos-aarch64" -pr:b="$CI_REPO_ROOT/ci/conan/profiles/ohos-aarch64" --build=missing --build=libjodycode/* -o libjodycode/*:shared=False`
- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-libjodycode-4.1.2-static-libjodycode-4.1.2-1410-20260725-071503-conan-static-20260725-074355-35729`
- Result: pass, exit code 0.
- Evidence: static package contained `libjodycode.a`, header, and manpage; `test_package` built and ran `libjodycode 4.1.2 consumer API test: OK`.

Earlier device failures and fixes:

- RUN_DIR `/storage/Users/currentUser/ohos-test-runs/codex-libjodycode-4.1.2-libjodycode-4.1.2-1410-20260725-071503-conan-20260725-073659-28748` failed because `test_package` used `JC_ENULL` as an index for `jc_get_errname()`/`jc_get_errdesc()`. Upstream `error.c` expects table indexes `0..15`; the consumer test now checks index `1`.
- An earlier run failed because `test_package` hardcoded `/data/service/hnp/bin/bash`; it now resolves a valid `CONFIG_SHELL` or PATH `bash`.

## Commands For Re-run Device/Shadow CI

Run only after apache-arrow is idle and a non-invasive runner lock/load check is clear. Do not use default `$HOME/.conan2` or a shared `$HOME/validation/build_in_harmonyos` workdir directly. Record the actual runner `RUN_DIR` in the handoff/PR notes.

After the branch is pushed or otherwise made available to the device, prepare an isolated job:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex-libjodycode \
  --job libjodycode-4.1.2-1410 \
  --package archives/l/libjodycode/4.1.2 \
  --repo-url https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git \
  --branch feat/libjodycode-4.1.2
```

Run the single-package heavy validation from the generated job only:

```sh
. "$HOME/ohos-users/codex-libjodycode/libjodycode-4.1.2-1410/env.sh"
cd "$CI_REPO_ROOT"
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```
