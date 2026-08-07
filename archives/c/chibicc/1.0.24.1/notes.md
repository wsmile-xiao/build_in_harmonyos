# chibicc 1.0.24.1 HarmonyOS adaptation notes

## Status

- Branch: `feat/chibicc-1.0.24.1-1894`
- Issue: `1894`
- Current state: preflight complete; R39 source URL switched to Debian primary sourcefiles authority mirror; OHOS shadow CI r7 passed.

## W0 Dependency Check

- Direct Conan dependency: `openssl/3.5.6.1`.
- Reason: upstream Makefile links `-lcrypto`; source uses libcrypto symbols through the build/link surface.
- Local remote verification: not run because `conan` is not installed in this Windows environment.
- Repository evidence: `archives/o/openssl/3.5.6.1` exists in this worktree; `curl/8.15.0` also uses `openssl/3.5.6.1` for OHOS compatibility.
- Dependency split requirement: no new dependency adaptation is included in this PR; if `openssl/3.5.6.1` is missing from the target remote, chibicc should pause until that dependency is published.

## Source and Build Analysis

- Source: Debian primary sourcefiles authority mirror for `chibicc_1.0.24.1.orig.tar.gz`.
- SHA256: `cbcdaccce25508566b77f26e2ffab41a379e05b6a0be73a5b6806796db62fecc`.
- Source URL: `https://launchpad.net/debian/+archive/primary/+sourcefiles/chibicc/1.0.24.1-1/chibicc_1.0.24.1.orig.tar.gz`.
- R39 source check: `rui314/chibicc` has no `v1.0.24.1` GitHub tag, so the final recipe uses the Debian primary sourcefiles authority mirror, whose tarball SHA256 matches the expected source integrity value.
- Build system: plain Makefile; recipe compiles directly with the Conan C compiler because the current OHOS runner has no `make` binary.
- CMake status: not used. The bundled `CMakeLists.txt` requires Boost and appears inconsistent with the C-only Makefile build.
- Main binary: `chibicc`.
- External link dependency: `libcrypto`.
- Architecture limitation: generated code is x86-64 assembly/object code. On OHOS/armv8, tests should verify the compiler binary and generated assembly instead of running generated executables.

## Recipe Notes

- Uses `tools.build:compiler_executables` to obtain the C compiler and passes it as `CC=...`.
- Reconstructs upstream `CFLAGS` so OpenSSL include paths from Conan are included.
- Passes `GCC_VERSION=0` to avoid running host `gcc -dumpversion` from the Makefile during cross builds.
- Builds the top-level `*.c` source set directly with the Conan C compiler, matching the upstream Makefile source list without requiring `make` on the target runner.
- Packages `bin/chibicc`, bundled headers under both `bin/include` and `include/x86_64-linux-gnu/chibicc`, and the MIT license.
- On OHOS, attempts to self-sign `bin/chibicc` when `/data/service/hnp/bin/binary-sign-tool` is available.

## Upstream Test Inventory

- `make test` builds many `test/*.c` files with the just-built `chibicc`, links them with the host compiler, and executes the generated programs.
- `make test-stage2` bootstraps a stage2 compiler and repeats executable tests.
- These upstream tests are valuable on Linux/x86-64 but not suitable as-is for OHOS/armv8 because generated x86-64 executables cannot run on the target.
- This recipe does not run upstream tests during `build()`.

## Local Preflight Results

- Downloaded the Debian primary sourcefiles tarball and verified its SHA256 locally.
- Inspected source archive contents: `Makefile`, `CMakeLists.txt`, `include/`, `test/`, `issues/`, and compiler source files.
- Identified `openssl/3.5.6.1` as the only Conan dependency.
- First OHOS shadow CI attempt reached `conan create` but failed because the isolated `CONAN_HOME` lacked the `ohpcd` remote; adding `ohpcd` resolved dependency lookup.
- Second OHOS shadow CI attempt downloaded `openssl/3.5.6.1` from `ohpcd` and then failed because `make` is not available in the runner PATH; recipe was updated to compile directly with clang.
- Third OHOS shadow CI attempt initially could not start because the device reported `/bin/sh: Out of memory`, `can't fork`, and then SSH port `2222` refused connections.
- After device recovery at `2026-08-06 22:14:49 +08:00`, the direct-clang recipe was rerun. It built, packaged, and signed chibicc successfully, then failed in `test_package` because shell here-doc creation used read-only `/tmp`. The smoke script now uses package-local `TMPDIR`/`TMPPREFIX` and `printf` fixture generation.
- Fourth OHOS shadow CI attempt built, packaged, and signed chibicc successfully, then failed only because the smoke test expected a direct `call add`; generated assembly uses an indirect `call *%r10`. The assertion now checks for a call instruction without binding to that backend detail.
- Fifth OHOS shadow CI attempt passed on `2026-08-06`: `conan create` passed, `test_package` executed, `chibicc --version` passed, and the summary reported `Success: 1`, `Failed: 0`.
- Sixth OHOS shadow CI attempt passed after the R39 source fix: Conan downloaded sources from the official GitHub tag URL, `conan create` passed, `test_package` executed, `chibicc --version` passed, and the summary reported `Success: 1`, `Failed: 0`.
- The R39 source URL was revised again after review: the source now uses the Debian primary sourcefiles authority mirror.
- Seventh OHOS shadow CI attempt passed after the authority-mirror source fix: Conan downloaded sources from Launchpad Debian primary sourcefiles, `conan create` passed, `test_package` executed, `chibicc --version` passed, and the summary reported `Success: 1`, `Failed: 0`.
- Local `conan create` was not run because `conan` is not installed in this Windows environment.

## Verification Commands

```sh
cd /path/to/build_in_harmonyos

conan create archives/c/chibicc/1.0.24.1 --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos \
  -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing

CI_PACKAGES="archives/c/chibicc/1.0.24.1" zsh ci/conan/build_and_test.sh

# If using the shadow CI runner:
/path/to/run-ohos-shadow-ci.sh archives/c/chibicc/1.0.24.1
```

## Blocking Points

- `conan` is missing from the Windows PATH, so local Windows `conan create` could not be executed here.

## Final Status

- Preflight adaptation is complete: W0 dependency analysis, source/build-system analysis, Conan recipe, and non-empty test_package are prepared.
- OHOS shadow CI r7 passed in `/storage/Users/currentUser/ohos-test-runs/currentUser-chibicc-chibicc-1.0.24.1-1894-conan-r7-r39-authority-mirror-20260807-003457-40949`.
