# m4 1.4.19 adaptation notes

## Scope

- Target package: `m4/1.4.19`
- Branch: `feat/m4-1.4.19`
- Worktree: `D:\harmonyos\worktrees\m4`
- Issue: not found in local project files or handoff context; pending issue number in PR/handoff.
- This task is independent from `autoconf/2.72` and `libao/1.2.2`; those worktrees were only read for context.

## Version confirmation

- Downstream blocker: `D:\harmonyos\worktrees\autoconf\archives\a\autoconf\2.72\notes.md` records `m4/1.4.19` as the missing hard dependency for `autoconf/2.72`.
- Existing archive: `archives/m/m4/1.4.19` already existed, but it lacked `conanfile.py`, `conandata.yml`, `test_package`, and software-level `commands.json`.
- Upstream source: GNU FTP provides `https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz`.
- Downloaded SHA-256: `3be4a26d825ffdfda52a56fc43246456989a3630093cced3fbddf4771ee58a70`.
- Build system: release tarball contains `configure`, `configure.ac`, `Makefile.am`, `Makefile.in`, `checks/`, and `tests/`; this is an Autotools project.

## W0 dependency and remote checks

Commands run:

```sh
conan --version
conan remote list
conan list "m4/*" -r=ohpcd
conan download "m4/1.4.19" -r=ohpcd --only-recipe
conan list "autoconf/*" -r=ohpcd
```

Results:

- Conan version: `2.29.1`.
- `ohpcd` remote is enabled.
- `m4/*`: 0 matching recipes in `ohpcd`.
- Direct `m4/1.4.19` recipe download failed with `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`.
- `autoconf/*`: also 0 matching recipes in `ohpcd`, consistent with the downstream blocker.
- m4 itself has no Conan package dependencies; `--disable-nls` is used to avoid pulling gettext/libintl into this build-tool package.

## Existing archive audit

- Removed six legacy patches from 2026-04-26.
- `0001-build-aux-config.guess.patch` and `0002-build-aux-config.sub.patch` were large GNU config refreshes and did not apply cleanly to the official tarball in this worktree.
- `0004-doc-stamp-vti.patch` and `0005-doc-version.texi.patch` contained a captured OHOS runtime environment dump inside generated documentation metadata; these were invalid for reproducible packaging.
- Kept the actual adaptation intent as four smaller patches:
  - `0001-recognize-ohos-triplet-config-guess.patch`
  - `0002-recognize-ohos-triplet-config-sub.patch`
  - `0003-use-readable-configure-tempdirs.patch`
  - `0004-port-freadahead-to-ohos.patch`

## Recipe and tests

- Added `conanfile.py` with `package_type = "application"`.
- Added `conandata.yml` with GNU source URL, SHA-256, and patch declarations.
- Added software-level `commands.json` because m4 installs the `m4` CLI command.
- Added `test_package` that uses `m4` as a Conan build tool, runs `m4 --version`, expands `test.m4`, and verifies macro expansion, arithmetic, and conditional output.
- OHOS builds define `GNULIB_FREADAHEAD_OPAQUE_FILE` through `AutotoolsToolchain.extra_defines`; the `freadahead.c` patch uses that build-selected generic feature macro instead of an OHOS source-level conditional.
- The custom OHOS configure path uses explicit public configure arguments and `shlex.join`, avoiding Conan private `Autotools._configure_args` access.
- On OHOS, the recipe runs a build-output smoke test using `build-release/src/m4` on `conan-smoke.m4`; the packaged `test_package` then verifies the installed `m4` command.
- Linux builds keep the upstream `make check -j1` path. Full OHOS `make check` was attempted during device validation and failed only in platform-sensitive test harness cases (`checks/198.sysval` and `checks/stackovf.test`), so it is not used as the OHOS package gate.

## Local verification

Checks run on the Windows host:

```powershell
python -m py_compile archives\m\m4\1.4.19\conanfile.py archives\m\m4\1.4.19\test_package\conanfile.py
python -m json.tool archives\m\m4\commands.json
conan export archives\m\m4\1.4.19
conan inspect archives\m\m4\1.4.19
conan create archives\m\m4\1.4.19 --build=missing
git -C <unpacked-m4-1.4.19> apply --check --verbose archives\m\m4\1.4.19\patches\*.patch
```

Current status:

- Local recipe and metadata are prepared and exported successfully.
- Latest local `conan export` passed as `m4/1.4.19#9cbb528c6b54dec7c6bd18331332739b`.
- `conan inspect` shows `package_type: application`, no requirements, and all four patches in `conandata`.
- `conan create --build=missing` on the Windows host stopped at validate with `Invalid: m4 is adapted for Linux and OHOS only`; this is expected because the local default profile is `Windows/msvc/x86_64`.
- Device isolated `conan create` passed on OHOS in r13, including build-output smoke, package install, `test_package`, destructive negative test, and `m4 --version` smoke.

## OHOS isolated validation

Device context used the required isolated runner and isolated Conan home:

- Job base: `/storage/Users/currentUser/ohos-users/codex-m4/m4-1.4.19`
- `CONAN_HOME`: `/storage/Users/currentUser/ohos-users/codex-m4/m4-1.4.19/conan-home`
- Runner: `$HOME/bin/ohos-test-runner.sh`
- Passing run: `/storage/Users/currentUser/ohos-test-runs/codex-m4-m4-m4-1.4.19-conan-r13-20260805-201251-20896`
- Remote package reference from r13: `m4/1.4.19#742c610ff5b187749039a710c4410aef:6b129b068851896169fae42d399fa922d239ce8a#311d22d7a0294b9473d8c0a5b90cf75a`

Important device findings:

- The copied OHOS profile initially pointed `CONFIG_SHELL`, `SHELL`, `CC`, and `CXX` through `/storage/Users/currentUser/usr/local/bin/bash`, but that bash path did not exist on the device.
- The recipe now selects an executable shell (`/bin/sh` or `/system/bin/sh`) and strips stale shell wrappers from compiler commands when the real compiler path is executable.
- Configure needed LLVM binutils explicitly in the Autotools environment (`LD=ld.lld`, `AR=llvm-ar`, `RANLIB=llvm-ranlib`, optional `NM=llvm-nm`) to pass linker/tool detection.
- r9 full OHOS `make check` built successfully but failed two upstream harness checks: `checks/198.sysval` had unexpected stderr `Signal 9`, and `checks/stackovf.test` hit temporary-file permission behavior under the isolated OHOS filesystem.
- r13 passed after the review fixes; CI L1/L2/L5 passed, with only L4 warning on patch text containing a dangerous-function-looking string from `config.guess` pattern data.

## Rerun OHOS device / shadow CI commands

Use the isolated runner/job entrypoints; do not use shared `CONAN_HOME` or a shared validation checkout.

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex-m4 \
  --job m4-1.4.19 \
  --package archives/m/m4/1.4.19 \
  --repo-source "$HOME/validation/build_in_harmonyos"

. "$HOME/ohos-users/codex-m4/m4-1.4.19/env.sh"
cd "$CI_REPO_ROOT"
git fetch origin feat/m4-1.4.19
git checkout feat/m4-1.4.19
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```

Single-package CI command once inside the isolated repo:

```sh
CI_PACKAGES="archives/m/m4/1.4.19" zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/m/m4/1.4.19
```
