# autoconf 2.72 adaptation notes

## Scope

- Target package: `autoconf/2.72`
- Branch: `feat/autoconf-2.72`
- Worktree: `D:\harmonyos\worktrees\autoconf`
- Issue: not found in local project files or handoff context; pending issue number in PR/handoff.
- Do not mix this into `libao`; `D:\harmonyos\worktrees\libao` was not modified.

## Version confirmation

- Repo/index: `archives/_index.yaml`, `SUMMARY.md`, and `scripts/ohc/dependency_resolver.py` point to Autoconf 2.72.
- Existing archive: `archives/a/autoconf/2.72` already existed but lacked `conanfile.py`, `conandata.yml`, `test_package`, and `commands.json`.
- Upstream: GNU FTP provides `autoconf-2.72.tar.gz`; downloaded SHA-256 is `afb181a76e1ee72832f6581c0eddf8df032b83e2e0239ef79ebedc4467d92d6e`.
- Source mirror note: PR CI build #15421 failed before recipe execution while downloading the PR diff from `gitcode.com`, not while downloading Autoconf. However, the same CI diagnostic says `ftp.gnu.org` is not reachable from the worker, so `conandata.yml` now tries TUNA, Aliyun, and `mirrors.kernel.org` GNU mirrors before falling back to the official GNU FTP URL. The SHA-256 remains the official tarball hash.
- Upstream also has newer Autoconf 2.73, but the current project dependency mapping still targets 2.72.

## W0 dependency and remote checks

Commands run:

```sh
conan list "autoconf/*" -r=ohpcd
conan download "autoconf/2.72" -r=ohpcd --only-recipe
conan list "m4/*" -r=ohpcd
conan download "m4/1.4.19" -r=ohpcd --only-recipe
conan list "m4/1.4.19:*" -r=ohpcd
conan download "m4/1.4.19" -r=ohpcd
conan list "perl/*" -r=ohpcd
conan list "perl/5.42.2:*" -r=ohpcd
conan download "perl/5.42.2" -r=ohpcd --only-recipe
conan list "automake/*" -r=ohpcd
conan list "libtool/*" -r=ohpcd
curl -I -L https://mirrors.tuna.tsinghua.edu.cn/gnu/autoconf/autoconf-2.72.tar.gz
curl -I -L https://mirrors.aliyun.com/gnu/autoconf/autoconf-2.72.tar.gz
curl -I -L https://mirrors.kernel.org/gnu/autoconf/autoconf-2.72.tar.gz
```

Results:

- `autoconf/*`: 0 matching recipes in `ohpcd`; direct download failed with `system acceleration policy not enabled`.
- `perl/5.42.2`: visible in `ohpcd`; recipe already present in local cache.
- `perl/5.42.2:*`: OHOS armv8 package `6b129b068851896169fae42d399fa922d239ce8a` visible in `ohpcd`.
- Earlier `m4/*` checks returned 0 recipes while the dependency adaptation was still pending.
- 2026-08-06 recheck after the `m4` merge: `m4/1.4.19` is visible in `ohpcd`; recipe revision `9a84a566238ea69b63e725d646354933` and OHOS armv8 package revision `8b566d24f4ee8ccaea3bc86a3eb00a93` downloaded successfully.
- `automake/1.18` and `libtool/2.5.4`: visible in `ohpcd`; useful for downstream `autoreconf`, but not built into this package.
- 2026-08-07 source mirror check from local Windows: TUNA, Aliyun, and `mirrors.kernel.org` returned HTTP 200 for `autoconf-2.72.tar.gz`; USTC returned HTTP 403 and was not added; `ftpmirror.gnu.org` timed out in 30 seconds.

Dependency status:

- `m4/1.4.19` is no longer the active blocker for `autoconf/2.72`; the isolated OHOS device run now resolves and uses both `m4/1.4.19` and `perl/5.42.2` from `ohpcd`.

## Source and build-system analysis

- Official release tarball contains `configure`, `configure.ac`, `Makefile.in`, `bin/*.in`, and `build-aux/config.guess/config.sub`.
- Build system is Autotools; recipe uses `configure && make -j1 && make install`.
- No `autoreconf` is needed to build Autoconf itself.
- Autoconf installed commands are Perl scripts that need `perl`, `m4`, and the package's `share/autoconf` data directory at runtime.

## Changes prepared

- Added `conanfile.py` with `package_type = "application"`.
- Added `conandata.yml` with official GNU source URL, SHA-256, and patch declaration.
- Added software-level `commands.json` because Autoconf installs CLI commands.
- Added `test_package` that runs the installed commands, uses `autoconf`/`autoheader` to generate a minimal `configure` project, and directly exercises `autom4te` macro processing.
- Replaced six old hardcoded/generated-file patches with one portability patch for `config.guess` and `config.sub`.
- Added wrapper scripts after install so `share/autoconf` paths are derived from the package prefix instead of baked absolute paths.
- The `autom4te` wrapper prepends the current package `share/autoconf` directory on every invocation. This compensates for upstream `autom4te.cfg` being configured with `//share/autoconf` when Conan installs with `DESTDIR`.

## Local verification

Checks run:

```powershell
python -m py_compile archives\a\autoconf\2.72\conanfile.py archives\a\autoconf\2.72\test_package\conanfile.py
conan export archives\a\autoconf\2.72
git -C <unpacked-autoconf-2.72> apply --check --verbose archives\a\autoconf\2.72\patches\0001-support-linux-ohos-config-triplet.patch
conan create archives\a\autoconf\2.72 --build=missing
conan create archives\a\autoconf\2.72 -pr:h=ci\conan\profiles\ohos-aarch64 -pr:b=ci\conan\profiles\ohos-aarch64 --build=autoconf/*
```

Results:

- Python syntax check: pass.
- YAML/JSON metadata parse check: pass.
- Patch apply check against the official 2.72 tarball: pass.
- `conan export`: pass; latest exported recipe revision after the true-device profile fixes is `autoconf/2.72#ded5821bccb80a62dddc24f4b5002f07`.
- First `conan create`: blocked during dependency graph resolution because `m4/1.4.19` was not yet in local cache or `ohpcd`.
- 2026-08-06 `conan create` with OHOS profile: dependency graph resolved with `m4/1.4.19` and `perl/5.42.2` from cache/`ohpcd`.
- The same run initially caught stale hunk line numbers in `0001-support-linux-ohos-config-triplet.patch`; the patch was refreshed and then applied successfully during Conan `source()`.
- Current local Windows limit: build reaches `autotools.configure()`, then fails with `'.' is not recognized as an internal or external command` because this host cannot execute the POSIX `configure` script under the OHOS profile. True OHOS runner verification has passed.
- 2026-08-07 true-device reruns with the current OHOS profile first exposed `CONFIG_SHELL=/data/service/hnp/bin/bash` from `ci/conan/profiles/ohos-aarch64`; that path is not present on the current device. The recipe now overrides `SHELL` and `CONFIG_SHELL` in the generated Conan build environment with the executable shell discovered by `_config_shell()`, which resolves to `/bin/sh` or `/system/bin/sh` on current OHOS devices. The profile also defines `PATH` directly, so test_package adds autoconf, m4, and perl package `bin` directories through an explicit `autoconf_test_env` script after `conanbuild`.

## OHOS isolated device verification

Initial Windows PowerShell SSH checks were blocked by the remote endpoint closing before the SSH banner. After the device window became available, the isolated job was created at:

```text
/storage/Users/currentUser/ohos-users/codex-autoconf/autoconf-2.72
```

Because the branch was not pushed, local `archives/a/autoconf` was transferred as a tarball and extracted only into the isolated repo:

```powershell
ssh -T -p 33332 -i "$env:USERPROFILE\.ssh\ohos_pc_codex_ed25519" currentUser@frp-tip.com
```

Runner command:

```sh
. "$HOME/ohos-users/codex-autoconf/autoconf-2.72/env.sh"
cp "$HOME/.conan2/settings.yml" "$CONAN_HOME/settings.yml"
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```

Final successful run:

```text
/storage/Users/currentUser/ohos-test-runs/codex-autoconf-autoconf-autoconf-2.72-pr4410-122fa92-conan-rerun5-testenv-20260807-182328-20260807-182328-47927
```

Result:

- Exit code: 0.
- `L0_RESULT=pass: all checks passed`.
- `L1_RESULT=pass: test_package executed`.
- `L5_RESULT=pass: bin/ has content`.
- `L4_RESULT=warn: dangerous functions in patches`; warning comes from portability patch content and is non-blocking in this run.
- `L2_RESULT=skip`: generic direct `bin/* --version/--help` probe does not load Conan dependency PATH, so Perl-backed Autoconf wrapper commands cannot find `perl`/`m4` there. The explicit `test_package` runs with `env=["conanbuild", "autoconf_test_env"]` and verifies command startup by name, `autoconf`/`autoheader` generation, `autom4te` macro processing, generated `configure`, and `config.h.in`.

Additional test-package findings:

- Running generated `configure` is intentionally not part of the final smoke test because the runner user's `/tmp` behavior is inconsistent: shell here-doc temp files may attempt `/tmp/sh*.tmp` and fail with `Read-only file system`.
- `autoreconf --force --install` is not part of the final smoke test because it can call optional `aclocal`; that belongs to Automake, not Autoconf's independent package.

Successful package reference:

```text
autoconf/2.72#ded5821bccb80a62dddc24f4b5002f07:6b129b068851896169fae42d399fa922d239ce8a#8a1aae9d15192163ba32f34e79cdc95c
```

## Upstream `make check` on OHOS

After the Conan package L0/L1/L5 verification passed, a separate upstream Autotest run was executed from a clean source copy in the same isolated OHOS job area. This run was not added to the recipe build flow.

Run directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-autoconf-autoconf-autoconf-2.72-upstream-make-check-clean-sh-20260806-200600-13526
```

Source workdir:

```text
/storage/Users/currentUser/ohos-users/codex-autoconf/autoconf-2.72/upstream-check-clean-sh-20260806-200601/src
```

Command outline:

```sh
./configure --disable-dependency-tracking --disable-silent-rules
make -j1 MAKEINFO=true
make check -j1 MAKEINFO=true TESTSUITEFLAGS="-j1"
```

The test environment used `perl/5.42.2` and `m4/1.4.19` from the isolated Conan cache, set `PERL5LIB` for packaged Perl modules, used `/bin/sh` as `SHELL`/`CONFIG_SHELL`, and kept `TMPDIR`/`TMPPREFIX` inside the isolated job directory. Generated Autotools files were timestamp-adjusted after copying the Conan source cache so the run would not try to rebuild release-generated files with missing `aclocal-1.16`.

Result:

- Exit code: 2.
- Official summary: `ERROR: 539 tests were run, 247 failed (5 expected failures). 70 tests were skipped.`
- Inventory: 609 GNU Autotest cases total; 70 skipped; 539 non-skipped cases executed.
- Pass-rate statement for PR: 297/539 (about 55.1%) when counting 292 `ok` cases plus 5 expected failures as expected outcomes; 242 unexpected failures remain.
- Failure clusters are mainly OHOS shell/path/temp-directory semantics and generated configure probes across Autoconf's language, compiler, header, type, function, and program macro suites.

## Next OHOS device / shadow CI commands

After the branch is pushed, rerun from a fresh isolated repo with:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex-autoconf \
  --job autoconf-2.72 \
  --package archives/a/autoconf/2.72 \
  --repo-source "$HOME/validation/build_in_harmonyos"

. "$HOME/ohos-users/codex-autoconf/autoconf-2.72/env.sh"
cd "$CI_REPO_ROOT"
git fetch origin feat/autoconf-2.72
git checkout feat/autoconf-2.72
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```

Single-package CI command once inside the isolated repo:

```sh
CI_PACKAGES="archives/a/autoconf/2.72" zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/a/autoconf/2.72
```
