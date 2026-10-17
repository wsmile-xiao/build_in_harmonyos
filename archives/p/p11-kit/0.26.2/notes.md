# Adaptation notes: p11-kit 0.26.2

## Scope

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2074
- Dedicated worktree: `D:/harmonyos/worktrees/p11-kit`
- Dedicated branch: `feat/p11-kit-0.26.2-2074`
- Allowed path: `archives/p/p11-kit/0.26.2/`

## Current status

Built and tested on a HarmonyOS aarch64 device. The selected configuration has
no required Conan dependencies; the recipe, focused upstream tests, consumer
test package, installation layout, and signed package artifacts passed Shadow
CI.

## Local validation

- The release archive SHA-256 matches `conandata.yml`.
- The extracted Meson project declares version 0.26.2 and registers all four
  selected upstream tests.
- Both Python files pass AST parsing; `git diff --check` reports no errors.
- The repository pre-commit checks report zero errors. The only warning is the
  repository preference for a GitCode source mirror; the verified official
  release URL is retained because no matching mirror URL was confirmed.
- Git scope inspection reports changes only under this version directory.
- Shadow CI subsequently completed `conan create`, ELF/SONAME inspection, and
  test execution on the target device.

## Shadow CI attempt 1

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/5c741288fd25-20260812T054231Z-run-51479`
- Setup: passed with Conan 2.29.1.
- Source download and Meson configure: passed.
- Build: failed at 24/245 with exit code 126 because the device filesystem
  rejected direct execution of `p11-kit/gen-pkcs11-gnu.sh`.
- Diagnosis: the script works through `/bin/sh`; `common/unix-peer.c` compiled,
  so the first `SO_PEERCRED` checkpoint passed.
- Fix: `0001-run-shell-scripts-via-sh.patch` makes Meson invoke both the generated-header
  script and post-install script through `sh`, avoiding direct script execution.

## Shadow CI attempt 2

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/b6880ea0b165-20260812T055131Z-run-11719`
- Setup and input verification: passed.
- Build: stopped before configure because Conan `patch_ng` requires exact hunk
  line numbers and rejected the first hunk's one-line offset.
- Fix: corrected the first hunk start from line 154 to line 155; no source change
  beyond the already planned shell invocation is introduced.

## Shadow CI attempt 3

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/05afa59fd704-20260812T055923Z-run-29952`
- Build: all 245 targets compiled successfully.
- Upstream tests: `test-version`, `test-uri`, `test-rpc`, and
  `test-rpc-message` all passed (4/4).
- Install: failed because Conan's Meson defaults set `libexecdir=bin`, causing
  private `bin/p11-kit/p11-kit-remote` to collide with the public `bin/p11-kit`
  executable.
- Probe: reconfiguring the completed build with `-Dlibexecdir=libexec` produced a
  complete installation with the expected public/private layout and exit code 0.
- Fix: the recipe now sets `libexecdir=libexec` explicitly.

## Shadow CI attempt 4

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/a890d19e103c-20260812T061903Z-run-57102`
- Build and install: all 245 targets compiled; four focused upstream tests
  passed; installation, alias materialization, and HarmonyOS ELF signing passed.
- Consumer link: failed because `p11_kit_check_version` is implemented and
  declared as public in 0.26.2, but the upstream `libp11-kit.map` omits it and
  hides it through the map's `local: *` rule.
- Diagnosis: `llvm-nm` confirms the symbol exists in `util.c.o` but is absent
  from both the unsigned and signed shared-library dynamic symbol tables.
- Fix: `0002-export-check-version.patch` adds the public API to the existing
  `LIBP11_KIT_1.0` export list; the consumer test remains unchanged.

## Shadow CI attempt 5

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/a93bb569da1e-20260812T063226Z-run-1859`
- Result: passed; runner setup and build both returned 0.
- Build and upstream tests: all 245 targets compiled and `test-version`,
  `test-uri`, `test-rpc`, and `test-rpc-message` passed (4/4).
- Consumer: CMake target linking and all 11 runtime assertions passed. The
  runner's destructive negative test also confirmed the test uses the package.
- Gates: L0, L1, L4, and L5 passed. L2 was non-blockingly skipped because the
  upstream command does not implement `--version`; with `LD_LIBRARY_PATH` set,
  `p11-kit --help` returns 0.
- Artifacts: `p11_kit_check_version@@LIBP11_KIT_1.0` is exported, the SONAME is
  `libp11-kit.so.0`, and `libexec/` is absent as required by the issue boundary.

## Shadow CI attempt 6 (final recipe bytes)

- Run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/d38d898eb43c-20260812T065733Z-run-23436`
- Snapshot commit: `d38d898eb43c9accdedf3e7c8aa6dbb2f8f26ecf`.
- Result: passed with setup/build return codes 0 and a 100% package pass rate.
- Gates and tests match attempt 5: L0/L1/L4/L5 passed, four upstream tests
  passed, all 11 consumer assertions passed, and the destructive negative test
  confirmed genuine package use. L2 remains a non-blocking CLI probe skip.
- Final artifact inspection again confirmed the versioned API export, SONAME,
  and absence of the server-owned `libexec/` directory.

## Official CI Worker variance and fix

- Official CI #22092 passed the complete pipeline on
  `OpenHarmonyPCDeveloper-CI-027` with the original recipe bytes.
- Official CI #22106 used the same branch commit and `main` base but failed on
  `OpenHarmonyPCDeveloper-CI-018` before compiling any p11-kit source. Meson's
  linker probe could not start the SDK `lld`: the ambient library search path
  selected an incompatible `libxml2.so.16`, producing unresolved `xml*`
  symbols.
- The recipe now resolves the real compiler path from
  `tools.build:compiler_executables`, locates the matching SDK `llvm/lib`, and
  prepends it to `LD_LIBRARY_PATH` for both the main Meson build and the CMake
  consumer build. This prevents worker-local libraries from shadowing the SDK
  runtime while retaining the existing paths for all other tools.
- The fix fails early with the resolved SDK directory when the matching
  `libxml2.so.16` is absent, rather than surfacing Meson's generic "Unable to
  detect linker" error.

## Next isolated runner command

Run only after a device/shadow-CI slot is assigned:

```sh
export RUN_DIR="${RUN_DIR:?runner must provide an isolated RUN_DIR}"
export TMPDIR="$RUN_DIR/tmp"
export TMPPREFIX="$RUN_DIR/tmp/zsh"
mkdir -p "$TMPDIR" "$TMPPREFIX"
CI_PACKAGES="archives/p/p11-kit/0.26.2" zsh ci/conan/build_and_test.sh
```

After a successful package build, verify the dependency chain separately:

```sh
conan list "p11-kit/0.26.2:*" -c
CI_PACKAGES="archives/p/p11-kit-server/0.26.2" zsh ci/conan/build_and_test.sh
```

The second command belongs to issue 2072 and must run from that issue's branch;
it must not be added to this PR.
