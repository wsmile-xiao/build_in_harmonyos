# perl 5.42.2 adaptation notes

## Scope

- Library: perl
- Version: 5.42.2, confirmed from `archives/_index.yaml`, `SUMMARY.md`, and `archives/p/perl/5.42.2/manifest.yaml`.
- Branch: `feat/perl-5.42.2-F72D`
- Worktree: `D:\harmonyos\worktrees\perl`
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1478

## Why this package is needed

`open-mpi/5.0.10` real-device Conan validation reached configure and failed with:

```text
configure: error: "Open MPI requires perl. Aborting"
```

The related `mpich/4.0.3` adaptation context also needs perl available during its build/configure flow. This package is therefore a build tool dependency for MPI recipes, not a dependency to mix into either MPI PR.

Recommended MPI consumer shape after this package is validated and published:

```python
def build_requirements(self):
    self.tool_requires("perl/5.42.2")
```

The perl recipe exposes:

- `buildenv_info.PATH += <package>/bin`
- `buildenv_info.PERL = <package>/bin/perl`
- `buildenv_info.PERL5LIB += <package>/lib/perl5/...`, including the generated arch-specific core module directories such as `aarch64-linux-thread-multi`

That should let Open MPI and MPICH configure scripts find `perl` through Conan's `VirtualBuildEnv` without relying on a system interpreter path on the device.

## W0 dependency check

`conan download "perl/5.42.2" -r=ohpcd --only-recipe` failed locally with:

```text
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
```

The existing origin/main archive had only `manifest.yaml` and `notes.md`, no `conanfile.py`, `conandata.yml`, or `test_package/`, so no Conan-consumable package was available in this worktree.

## Source and build system

- Source URL list, in Conan download order:
  - https://mirrors.tuna.tsinghua.edu.cn/CPAN/src/5.0/perl-5.42.2.tar.gz
  - https://mirrors.ustc.edu.cn/CPAN/src/5.0/perl-5.42.2.tar.gz
  - https://mirrors.aliyun.com/CPAN/src/5.0/perl-5.42.2.tar.gz
  - https://www.cpan.org/src/5.0/perl-5.42.2.tar.gz
- Source SHA256: `9384e8deb75b7b1695e5637971b752281aaecd025a3d5d4734d33c1d0adfee47`
- Analysis tarball: https://www.cpan.org/src/5.0/perl-5.42.2.tar.xz
- Analysis tar.xz SHA256: `0a585eeb9e363c0f80482ddb3571625250c2c86aeb408853e8ea50805cfb14bb`
- Build system: Perl's metaconfig `Configure`; `configure.gnu` is only a GNU-style wrapper.
- Upstream install supports `DESTDIR` during `make install`.
- Upstream tests: `make test_harness_notty` or `TEST_JOBS=N make test_harness`.

## Recipe strategy

The recipe is a native OHOS/Linux build tool package:

- Builds in-source because Perl's `Configure` rewrites files in the source tree.
- Runs `Configure` through a detected executable shell, not by executing the script directly.
- Forces `TMPDIR`/`TMPPREFIX` into the build directory to avoid read-only `/tmp` on the device.
- Uses Conan `tools.build:compiler_executables` to select the C compiler.
- Uses Linux hints for OHOS via `-Dosname=linux` and `-Darchname=aarch64-linux`.
- Avoids external DBM libraries by trimming `libswanted` and disabling `GDBM_File`, `NDBM_File`, `ODBM_File`, and `DB_File`.
- Excludes `IPC/SysV` on OHOS because the true-device upstream harness caught `SIGSYS` from SysV IPC runtime paths even though headers and symbols are detectable during configuration.
- Disables `HAS_PRCTL_SET_NAME` on OHOS with `-Ud_prctl_set_name`; the Configure probe uses a short process name that succeeds, while real `$0` assignments in the upstream suite fail with `EINVAL` and can hang child processes.
- Uses CPAN mirror fallback in `conandata.yml`; the first clean true-device run spent much of the 2700 second CI `conan create` timeout downloading from `www.cpan.org`.
- Forces `lns`/`LNS` to a build-local `ohos-ln-copy.sh` wrapper on OHOS because the true-device storage rejects hard links used by Perl's `GNUmakefile` for `opmini.c`, `perlmini.c`, and similar generated copies. The wrapper copies files and also resolves symlink-style relative sources such as `perldelta.pod -> pod/perl5422delta.pod` through the destination directory.
- Applies `patches/0001-miniperl-touch-noop.patch` so the generated `GNUmakefile` does not run `touch miniperl` after linking; the true-device storage permits executing the linked `miniperl` but rejects updating its timestamp.
- Applies `patches/0002-extutils-install-write-probe.patch` so `ExtUtils::Install` falls back to an actual create/unlink probe when `-w` or `POSIX::access(W_OK)` reports not writable even though OHOS storage permits writes.
- Applies `patches/0003-installperl-write-probe.patch` for the same OHOS storage behavior in `installperl`, where `DESTDIR/bin` can be created and written but Perl `-w` still reports false.
- Installs with `make install.perl DESTDIR=<package_folder>` to package interpreter and core modules without manpage generation.
- Signs packaged ELF files when the device signing tools are present.
- Exposes both pure and arch-specific `PERL5LIB` directories from `package_info()` so relocated `DESTDIR` installs can load core modules such as `Config.pm` when consumed through Conan `tool_requires`.

## Knowledge base references

Existing project knowledge that applies to this adaptation:

- `knowledge/doc/E002.md`: OHOS `/tmp` can be read-only or inaccessible; the recipe forces build-local `TMPDIR` and `TMPPREFIX`.
- `knowledge/doc/E018.md` and `knowledge/doc/E050.md`: OHOS/HMDFS link behavior can reject or fail to resolve symbolic-link style paths; the recipe replaces Perl's `lns` flow with a copy wrapper.
- `docs/ADAPTATION_GUIDE.md`: configure scripts should be run through an explicit shell on OHOS; the recipe detects `CONFIG_SHELL`/`SHELL` and invokes `Configure` through that shell.
- `knowledge/operations/dependencies.md`: Perl is a build-tool dependency for OpenSSL/autotools-style projects and is already identified as part of the lower toolchain layer.
- `archives/p/perl-mojolicious/9.42/notes.md`: prior Perl-module adaptation hit the same OpenHarmony `prctl(PR_SET_NAME)`/`$0` limitation and worked around module-level `$0` assignment with guarded save/restore logic. That prior art supports treating the Perl core harness `$0` failures as a known platform-sensitive area rather than an isolated package regression.

## Local verification

Performed in `D:\harmonyos\worktrees\perl` without starting real-device CI:

- Confirmed version from project metadata: `5.42.2`.
- Issue created: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1478
- Confirmed origin archive was missing Conan recipe/test inputs.
- `conan download "perl/5.42.2" -r=ohpcd --only-recipe` reproduced the remote acceleration-policy error.
- Downloaded `.tar.xz` for source analysis and verified SHA256.
- Inspected `Configure`, `configure.gnu`, `INSTALL`, and `hints/linux.sh`.
- Prepared `conanfile.py`, `conandata.yml`, and non-empty `test_package/`.
- `ast.parse` passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parsing passed for `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml`.
- `archives/p/perl/commands.json` is present at the required software-level path and validates as `type=tool`, `name=perl`, `versions["5.42.2"].ref=perl/5.42.2`.
- `conan inspect` loaded `perl/5.42.2` metadata successfully.
- `conan export ... --user=ohpcd --channel=stable` exported the recipe successfully.
- `conan graph info` with the repository OHOS aarch64 profile parsed with no dependencies and `info_invalid: None`.
- `git diff --check` reported only line-ending warnings for the rewritten tracked notes/manifest files.
- After fixing `patches/0002-extutils-install-write-probe.patch`, `git apply --check` against a clean Perl 5.42.2 source tree passed for the ExtUtils::Install fallback patch.

## True-device validation

Isolated job:

```text
/storage/Users/currentUser/ohos-users/codex-perl/perl-5.42.2-F72D-20260726-142000
```

Run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-155331-43099` passed source download/SHA256, unpack, recipe export, dependency graph, and Perl `Configure`. It then failed in `make` because `GNUmakefile` tried to create hard links:

```text
/system/bin/ln op.c opmini.c
ln: cannot create hard link from 'op.c' to 'opmini.c': Operation not permitted
```

At that point the recipe was changed to use `cp` instead of hard links, which allowed the next run to get further.

Run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-172018-34051` then reached and executed the linked `./miniperl`, but failed when the generated `GNUmakefile` ran `touch miniperl`:

```text
./miniperl -Ilib -f write_buildcustomize.pl
touch: 'miniperl': Permission denied
make: *** [GNUmakefile:386: miniperl] Error 1
```

The source patch now changes that generated rule to a no-op.

Run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-181025-64210` applied the patch, completed `Configure`, completed `make depend`, linked and executed `./miniperl`, and passed the previous `touch miniperl` point. It then failed because the earlier global `LNS=/system/bin/cp` did not preserve symlink-style relative source semantics in pod-generation rules:

```text
./miniperl -Ilib -f write_buildcustomize.pl
cp: bad '../README.aix': No such file or directory
...
rm -f pod/perl5422delta.pod
/system/bin/cp perldelta.pod pod/perl5422delta.pod
cp: bad 'perldelta.pod': No such file or directory
make: *** [GNUmakefile:436: pod/perl5422delta.pod] Error 1
```

Run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-200737` used the build-local `ohos-ln-copy.sh` wrapper. It completed source download/SHA256, patch application, `Configure`, `make depend`, hardlink replacement for `opmini.c`/`perlmini.c`/`universalmini.c`, `miniperl` link and execution, and the previous `pod/perl5422delta.pod` copy-link point:

```text
/bin/sh .../ohos-ln-copy.sh perldelta.pod pod/perl5422delta.pod
./miniperl -Ilib autodoc.pl
```

It then failed in `cpan/Archive-Tar` while `ExtUtils::Install::pm_to_blib` tried to create `../../lib/auto`:

```text
ERROR: Can't create '../../lib/auto'
Do not have write permissions on '../../lib/auto'
make: *** [GNUmakefile:599: cpan/Archive-Tar/pm_to_blib] Error 25
```

Follow-up probing in the same build directory showed shell and miniperl could create files/directories under `lib` and `lib/auto`, while Perl's `-w` reported false:

```text
shell_test_w_lib=0
touch_rc=0
mkdir_rc=0
lib e=1 d=1 w=0 x=1
lib/auto e=1 d=1 w=0 x=1
probe_e=1
```

The recipe now patches `cpan/ExtUtils-Install/lib/ExtUtils/Install.pm` to use an actual create/unlink probe as a fallback for unreliable write-permission tests.

Resume/debug run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-resume-0002-20260726-210152-27606` applied the same ExtUtils::Install fallback directly in the failed build directory, resumed `make -j1`, and completed with `exit_code=0`:

```text
Everything is up to date. Type 'make test' to run test suite.
```

This confirms the fallback itself unblocks the build stage. A clean true-device Conan CI run is still required because the earlier patch file had malformed hunk counts before it was corrected locally.

Clean CI run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-214823-54006` used corrected patches and proved:

- Source SHA256 check and both patches applied in a clean Conan source folder.
- `Configure` completed.
- `make depend`, copy-link wrapper, `miniperl`, `pod/perl5422delta.pod`, `cpan/Archive-Tar`, and all dynamic XS module build stages completed.
- `make` reached:

```text
Everything is up to date. Type 'make test' to run test suite.
```

The CI command still exited nonzero because `ci/conan/build_and_test.sh` wraps `conan create` in a 2700 second timeout; the slow official CPAN download plus Perl's long configure/build exceeded that window before package/test_package. `conandata.yml` now uses CPAN mirror fallback to reduce download time for the next clean run.

Clean CI run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-230905-46412` used mirror fallback and corrected build-stage patches. It completed source download/SHA256, patch application, `Configure`, `make depend`, `miniperl`, final `perl`, and the dynamic core/XS extension builds. It then failed in `package()`:

```text
./perl -Ilib -I. installperl --destdir=.../perl120b081ebe06d/p
.../perl120b081ebe06d/p//bin is not writable by you
make: *** [GNUmakefile:490: install.perl] Error 2
```

Follow-up probing in the same package directory showed Perl `-w` reported false while an actual file create/unlink succeeded:

```text
dash_w=0
open=1
```

The recipe now patches `installperl` to use the same create/unlink fallback for this install-stage write check.

Clean CI run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260726-235215-24863` proved patch 0003: `package()` completed, `installperl` installed the interpreter/core modules, and Conan created package revision `c2924fd3dbcce26aac41e1760fc25827`. The run then failed only in `test_package` because the Python-side precheck read `os.environ["PERL"]` before Conan's generated build environment was applied:

```text
AssertionError: perl was not exposed by the Conan build environment
```

The smoke test now lets `self.run(..., env="conanbuild")` apply the generated environment and relies on `test_perl.sh` to fail if `PERL`/`PATH`/`PERL5LIB` are not exposed correctly.

Final clean CI run `codex-perl-5.42.2-perl-5.42.2-F72D-20260726-142000-conan-20260727-002653-59772` passed end to end:

```text
[ok] perl/5.42.2 — conan create passed
perl 5.042002 ok
os=linux; arch=aarch64-linux-thread-multi; sep=a/b
script ok
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: corelist version/help failed, cpan failed, enc2xs failed, encguess failed, h2ph failed, h2xs failed, instmodsh failed, json_pp failed, libnetcfg failed, perl --version OK, perl5.42.2 --version OK, perlbug failed, perldoc failed, perlivp failed, piconv failed, pl2pm failed, pod2html failed, pod2man failed, pod2text failed, pod2usage failed, podchecker failed, prove failed, ptar failed, ptardiff failed, ptargrep failed, shasum failed, splain failed, streamzip failed, xsubpp failed, zipdetails failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Success: 1
Failed: 0
```

Package reference:

```text
perl/5.42.2#66357f3a7814ffa244bdfbe8bf1c2b86:6b129b068851896169fae42d399fa922d239ce8a#68082b6e1498fa256e37f3922e155302
```

Post-review clean rerun `codex-perl-5.42.2-conan-rerun-20260727-024352` was started after adding `archives/p/perl/commands.json` and updating `patches/0002-extutils-install-write-probe.patch` so the `POSIX::access(W_OK)` fast path uses Perl truth semantics (`return 1 if POSIX::access(...)`; successful `SysRet` values are truthy, including `0 but true`) before falling back to an actual create/unlink probe. It exited nonzero because the repository CI wrapper killed `conan create` at its 2700 second timeout:

```text
end_utc=2026-07-26T19:41:37.920977+00:00
elapsed_seconds=2703.7
exit_code=1
```

This rerun completed source/SHA256, patch application, `Configure`, `make depend`, hardlink replacement through `ohos-ln-copy.sh`, `miniperl`, generated `perl`, `pm_to_blib` for many core modules, and passed the earlier `ExtUtils::Install` write-probe failure point. It was interrupted during the dynamic XS build stage, around `Compress::Raw::Zlib`, before `package()` and `test_package`; stderr was empty and no new functional error was observed before timeout.

Follow-up true-device rerun `codex-perl-5.42.2-conan-after-fixes-20260727-081120` was launched with a writable `TMPDIR` for CI L0 heredocs and `PATH` including the device Conan entry points:

```text
TMPDIR=/storage/Users/currentUser/ohos-test-runs/codex-perl-5.42.2-conan-after-fixes-20260727-081120/tmp
PATH=$HOME/.local/bin:$HOME/ohpc-ci-shadow/python-user/bin:$PATH
CI_PACKAGES="archives/p/perl/5.42.2" zsh ci/conan/build_and_test.sh
```

This run proved the latest recipe changes through package creation:

```text
[ok] L0: All quality gate checks passed
[step] L0k: Checking commands.json for CLI tools (R38)...
        [ok] commands.json valid (type=tool)
Created package revision d8f9b5d50161ac009ed647586fab2d9a
Full package reference: perl/5.42.2#de213e597a9818c21c2a608c25de92b0:6b129b068851896169fae42d399fa922d239ce8a#d8f9b5d50161ac009ed647586fab2d9a
```

It then failed in `test_package` because the true-device work copy had CRLF line endings in `test_package/test_perl.sh`:

```text
test_perl.sh[2]: set: -\r: unknown option
```

After syncing the LF-normalized `test_perl.sh` to that same true-device test package directory, a lightweight smoke using the generated `conanbuild.sh` and already-created package passed without triggering another full build:

```text
no_cr_bytes
sh_n_ok
perl 5.042002 ok
os=linux; arch=aarch64-linux-thread-multi; sep=a/b
script ok
```

Per the user's instruction to pause after a failed full build, no further complete true-device `conan create` rerun was launched after this CRLF failure. The remaining verification gap is a fresh full Conan rerun proving the LF-normalized `test_package` through the CI wrapper end to end.

## Upstream test_harness_notty validation

Full upstream Perl test harness was run on the true device from the successful Conan build directory to provide audit evidence beyond the package smoke test.

Run directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-perl-5.42.2-upstream-test_harness_notty-20260727-012804
```

Command:

```sh
cd /storage/Users/currentUser/ohos-users/codex-perl/perl-5.42.2-F72D-20260726-142000/conan-home/p/b/perl901852186ce53/b
make test_harness_notty
```

Harness result:

```text
Files=2908, Tests=1348696, 2912 wallclock secs (101.32 usr 29.54 sys + 505.04 cusr 170.71 csys = 806.61 CPU)
Result: FAIL
Finished test run at Mon Jul 27 02:17:39 2026.
```

The wrapper `exit-code.txt` is `0`, but the upstream harness summary is authoritative here and reports `Result: FAIL`. The test run is therefore recorded as upstream test failure, not as a pass.

The summary contains 44 failing test-file entries, so the file-level upstream pass rate is `2864/2908` test programs (`98.49%`). The harness reports `Tests=1348696` actual subtests executed, but several failing test programs aborted early or produced TAP parse errors, so no reliable global passed-subtest count is claimed. Representative failure groups:

- Link and filesystem semantics: `cpan/Archive-Tar`, `ext/File-Find`, `op/stat.t`, `op/taint.t`, and `io/fs.t` fail around symbolic links, hard links, link counts, and symlink traversal on OHOS storage.
- Writable/permission-bit semantics: `cpan/ExtUtils-Install`, `cpan/File-Path`, `cpan/File-Temp`, `op/filetest.t`, `AnyDBM_File`, and `SDBM_File` expose the same `-w`/chmod/access mismatch that the recipe works around with actual create/unlink probes for build and install.
- POSIX/kernel feature gaps: `IPC-SysV`, `io/sem.t`, `POSIX::termios`, `POSIX::sigaction`, `Time::HiRes::itimer`, and `dist/IO/t/io_unix.t` fail around SysV IPC, errno differences, signal handling, virtual timers, and Unix-domain socket limits. `IPC/SysV` is now excluded for OHOS so the SysV IPC files should skip on a fresh rerun.
- Direct execution and script handling: `cpan/Test-Harness/t/source_handler.t` cannot directly execute `.sh` test scripts on the device (`Permission denied`), matching the recipe choice to run configure/tool scripts through an explicit shell.
- Process-name and `$0` handling: the original run showed `Can't set $0 with prctl(): Invalid argument` in `lib/warnings.t`, `op/leaky-magic.t`, `op/lex.t`, and `op/magic.t`; three child processes hung and were manually terminated so the harness could continue:
  - PID `60602`/`60601` from `lib/warnings.t` generated `tmp_CIWS_C`
  - PID `2021` from `op/leaky-magic.t`
  - PID `3285` from `op/magic.t`, shown as `[haha...]`
- Other platform-sensitive checks: `Time-Piece` timezone expectations, `run/locale.t` fallback message, `porting/globvar.t`, and selected ExtUtils::MakeMaker dynamic/static XS subtests fail, while the large regex, Unicode, thread, JSON, core language, and many XS API sections continue to execute successfully.

Follow-up fixes applied after this upstream analysis: the recipe now passes `-Ud_prctl_set_name` for OHOS and excludes `IPC/SysV` from OHOS extension builds. Source inspection shows `Configure` only probes `prctl(PR_SET_NAME, "Test")`, which succeeds with a short name, while runtime `$0` assignments with longer or empty values can fail with `EINVAL` in `mg.c`. This matches the earlier `perl-mojolicious/9.42` platform note. SysV IPC is likewise detectable but raises `SIGSYS` during upstream runtime tests. These changes need a fresh clean true-device Conan rerun for new package revision evidence.

All 44 failing upstream test-file entries have been closed in `upstream-failure-analysis.md` with per-file evidence, root cause, fixability judgment, and action or non-fix rationale.

No upstream test files were modified for this run. The failures are not treated as accepted upstream compatibility; they are documented as known limitations for a Path A build-tool adaptation. The Conan validation remains the acceptance gate for the immediate open-mpi/mpich use case because those consumers require `perl` as a configure/build tool available through Conan `tool_requires`, not full CPAN/runtime compatibility.

No separate upstream integration-test target was identified. Perl's `make test_harness_notty` is the combined core/CPAN/dist/ext/lib regression suite used here as the upstream test evidence.

## Future B-class knowledge note

No B-class application issue is submitted in this PR round; the user requested review of the final adaptation summary before any B-class issue is re-created.

This adaptation has B-class value because clean CI passed and it combines several reusable HarmonyOS native-build failure modes in one tool package:

- Build-local `TMPDIR`/`TMPPREFIX` for projects whose configure scripts assume writable `/tmp`.
- Shell-wrapping scripts or toolchain wrappers whose shebang points to unavailable or forbidden `/bin/sh`.
- Replacing hardlink/symlink build rules with copy semantics on OHOS storage while preserving relative source lookup.
- Avoiding timestamp-only `touch` updates on generated executables when the filesystem allows execution but denies metadata mutation.
- Treating Perl `-w` and `POSIX::access(W_OK)` as unreliable on this storage and falling back to an actual create/unlink write probe.

## Revalidation

Repeat the final true-device validation with:

```sh
CI_PACKAGES="archives/p/perl/5.42.2" zsh ci/conan/build_and_test.sh
```

To reproduce the upstream harness evidence from an existing successful Conan build folder:

```sh
cd /storage/Users/currentUser/ohos-users/codex-perl/perl-5.42.2-F72D-20260726-142000/conan-home/p/b/perl901852186ce53/b
make test_harness_notty
```

After perl is published, rerun the MPI consumers as separate PRs/jobs:

```sh
CI_PACKAGES="archives/o/open-mpi/5.0.10" zsh ci/conan/build_and_test.sh
CI_PACKAGES="archives/m/mpich/4.0.3" zsh ci/conan/build_and_test.sh
```

Do not modify the open-mpi or mpich PRs from this perl worktree; add `tool_requires("perl/5.42.2")` in those recipes only in their own branches after perl is validated/published.
