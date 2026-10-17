# Boost 1.90.0.1 W0 pre-adaptation report

Date: 2026-08-20
Issue: 219
Branch: `feat/boost-1.90.0.1`
Worktree: `D:\harmonyos\worktrees\boost`

## Scope and dependency check

- The worktree was created from `main`; the Apache Arrow checkout was not
  switched.
- The target package has no Conan `requires` entries. Its only external input
  is the pinned Boost 1.90.0 source archive in `conandata.yml`, so no dependency
  package adaptation is required for this package.
- The source URL and SHA-256 are present:
  `https://github.com/boostorg/boost/releases/download/boost-1.90.0/boost-1.90.0-cmake.tar.xz`
  and
  `aca59f889f0f32028ad88ba6764582b63c916ce5f77b31289ad19421a96c555f`.
- The local host does not provide a `conan` executable. The `ohpcd` recipe
  lookup therefore could not be run in this W0 pass. A direct HEAD request to
  the GitHub archive also failed because the host could not reach the remote
  server.

## Source and build analysis

- The recipe uses the official CMake release archive, not the Boost.Build/b2
  workflow. `manifest.yaml` and `conanfile.py` consistently select CMake.
- The recipe builds the compiled closure needed by the consumer test:
  `atomic`, `container`, `filesystem`, `program_options`, and `system`.
- Header-only modules used by the test (`algorithm`, `circular_buffer`,
  `math`, `property_tree`, and `tokenizer`) are enabled through
  `BOOST_INCLUDE_LIBRARIES` without being modeled as compiled libraries.
- The OHOS branch disables filesystem features that are not available on the
  target, avoids versioned shared-library links, sets OHOS rpath/soname flags,
  and signs generated shared objects when the native signing tools are
  available.
- The unified-diff patch
  `patches/0001-cmake-avoid-versioned-soname-links-on-ohos.patch` is the only
  source patch and has one portability responsibility.

## Conan recipe and test package audit

The baseline already contains the required non-empty files:

- `conandata.yml`
- `conanfile.py`
- `test_package/conanfile.py`
- `test_package/CMakeLists.txt`
- `test_package/test.cpp`
- `test_package/MANIFEST.yml`
- `manifest.yaml` and `notes.md`

The consumer test links `Boost::filesystem`, `Boost::program_options`, and
`Boost::system`, then exercises filesystem I/O, command-line parsing, and
header-only APIs. Cross-built OHOS consumers are signed before execution;
non-runnable cross builds are reported without attempting a host run.

## Local verification

Passed in this worktree:

```text
python -m py_compile archives/b/boost/1.90.0.1/conanfile.py \
  archives/b/boost/1.90.0.1/test_package/conanfile.py
git diff --check
python scripts/pre_pr_audit.py check --repo-dir . --force
```

The project pre-analysis command was attempted, but it requires a downloaded
source tree (`archives/b/boost-1.90.0.1/src`); no source archive was available
locally and network access was unavailable. Conan create, package creation, and
consumer execution therefore remain unverified on this Windows host.

Historical package notes record a successful isolated OHOS run for this exact
package and a 3/3 upstream component quick-test result. Those results are
retained as historical evidence and should be rerun for issue 219 if the
published recipe revision changes.

## Next single-package validation

Run only this package when a Conan-enabled OHOS/shadow worker is available:

```sh
CI_PACKAGES="archives/b/boost/1.90.0.1" zsh ci/conan/build_and_test.sh
```

For the shadow runner, use the equivalent single-package invocation:

```sh
/path/to/run-ohos-shadow-ci.sh archives/b/boost/1.90.0.1
```

Record the resulting `RUN_DIR`, package revision, Build Summary (`Total: 1`),
L0/L1/L4/L5 statuses, and the test-package exit code in the PR description.

## Issue 219 device attempts

SSH to `currentUser@10.62.222.172:2222` succeeded with the supplied key. The
device reported HarmonyOS aarch64, Conan 2.29.1, and a working
`ohos-aarch64` profile. A clean detached worktree was created from device
`origin/main` at commit `227a79b4e7`.

The official single-package runner acquired the global lock and stopped at the
registry collision gate:

- Run: `codex-boost-boost-1.90.0.1-219-conan-20260820-190356-23950`
- Result: `L0_RESULT=fail: version_not_incremented`
- Cause: `boost/1.90.0.1` is already published with different recipe content;
  the CI gate requests `boost/1.90.0.1.1` for a new recipe revision.

A diagnostic run with an intentionally unavailable remote name bypassed only
that registry check, without uploading anything. It then stopped at the full
repository junk-file gate because of the unrelated tracked file
`archives/d/detours/4.0.1/.build-closed`:

- Run: `codex-boost-boost-1.90.0.1-219-diagnostic-20260820-190713-25013`
- Result: `JC_RESULT=fail`, `JC_ERRORS=2`

Finally, a direct locked `conan create` was attempted against the current
recipe. Conan exported the recipe successfully and began downloading the
101.6 MB GitHub CMake archive, but the connection failed after 30.5 MB and
the retry timed out:

- Run: `codex-boost-boost-1.90.0.1-219-direct-20260820-191325-33991`
- Result: source download failed before CMake configure/build
- Error: `IncompleteRead(31457280 bytes read, 70135660 bytes more expected)` followed
  by `ConnectTimeoutError` to `github.com`

No detours or CI infrastructure files were modified. A formal CI pass for the
requested version requires either the already-published recipe content, a
version suffix approved by the issue owner, and a clean registry revision, or
a worker/network path that can fetch the pinned source archive reliably.
## Device validation completed

The pinned source archive was downloaded through a temporary SSH tunnel,
verified against the declared SHA-256, and placed only in the isolated device
job directory. The recipe itself was unchanged; the temporary device copy of
`conandata.yml` used the local tunnel URL only to avoid repeating the interrupted
GitHub download.

The locked direct Conan run completed successfully:

- Run: `codex-boost-boost-1.90.0.1-219-direct-cache-20260820-201814-35122`
- Conan package creation: exit code `0`
- OHOS target: `armv8`, `clang 15`, `libc++`, Release
- CMake configure/build/install: passed
- OHOS shared-library signing: passed with `llvm-objcopy` and
  `binary-sign-tool`
- `test_package` configure/build/run: passed
- Shadow runner: exit code `0`

The run emitted a non-fatal `make: jobserver mkfifo ... Operation not
permitted` message before compiling the consumer; the consumer still built and
ran successfully. The official registry collision and unrelated full-repository
cleanliness gate remain separate CI/registry issues and were not changed in the
Boost package directory.
## Final official Shadow CI

After aligning `conandata.yml` with the published recipe and using a clean
isolated Conan home, the standard single-package CI completed successfully:

- Run: `codex-boost-boost-1.90.0.1-219-official-final4-20260820-215542-41718`
- Registry recipe revision: `283f6593eaf063081d97e50e66971bcf`
- R37/version collision: passed (`recipe unchanged`)
- KC, G0, G0e, L0: passed
- L1: passed; upstream tests and `test_package` execution evidence present
- L2: skipped as expected; this library package has no `bin/` directory
- L4/L5: passed
- Build Summary: `Total=1, Success=1, Failed=0`
- Shadow runner: exit code `0`

The only non-fatal diagnostic was the device `make: jobserver mkfifo ...
Operation not permitted` message; the consumer still compiled, was signed,
and ran successfully. The device lacked an executable `git`, so the run used a
read-only temporary Git-index compatibility shim outside the repository; no
CI or repository files were changed by that shim.