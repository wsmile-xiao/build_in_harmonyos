# perl 5.42.2 upstream failure closure

Full upstream evidence was collected on the true device with:

```sh
cd /storage/Users/currentUser/ohos-users/codex-perl/perl-5.42.2-F72D-20260726-142000/conan-home/p/b/perl901852186ce53/b
make test_harness_notty
```

Harness summary:

```text
Files=2908, Tests=1348696, 2912 wallclock secs
Result: FAIL
```

The review inventory contains 2927 upstream test programs. The true-device harness run executed
2908 of them: 2864 passed and 44 failed. The conservative PR-level rate is therefore
`2864/2927`, or `97.85%`; the 19 inventory entries absent from this harness summary are not
counted as passed. A global subtest pass rate is not claimed because several programs aborted
early, had TAP parse errors, or were manually terminated after a hang.

## commands.json audit

`commands.json` is present at the required software-level path:

```text
archives/p/perl/commands.json
```

This is the path checked by `ci/conan/build_and_test.sh` L0k for a recipe under `archives/p/perl/5.42.2`. Local JSON validation confirms:

- `type == "tool"`
- `name` contains `perl`
- `versions` contains `5.42.2`
- `versions["5.42.2"].ref == "perl/5.42.2"`

The earlier lookup under `archives/p/perl/5.42.2/commands.json` was the wrong level and is not the CI-required location.

## Fixes applied after upstream failure analysis

- `-Ud_prctl_set_name` is added for OHOS. `Configure` only probes `prctl(PR_SET_NAME, "Test")`, which can pass, while real `$0` assignments with longer or empty values fail with `EINVAL` and can hang tests. Disabling only `HAS_PRCTL_SET_NAME` avoids shipping a broken `$0` update path while keeping the rest of `prctl` detection untouched.
- `IPC/SysV` is excluded from OHOS builds. Headers and symbols are detectable, but runtime SysV IPC paths raise `SIGSYS` on the true device. The package is a build-tool dependency for Open MPI and MPICH, and those consumers do not need `IPC::SysV`.

These changes need a fresh true-device Conan rerun for package revision evidence. Local recipe/metadata validation is recorded in `notes.md`.

## 44 failed test-file closure

| # | Test file | Evidence | Root cause | Fixability and closure |
| - | - | - | - | - |
| 1 | `../cpan/Archive-Tar/t/04_resolved_issues.t` | `Making symbolic link ... failed`; failed symlink extraction tests 46-48. | Archive::Tar is validating real symlink extraction. The OHOS storage used by the run rejects symlink creation with `Permission denied`. | Not fixed in Path A. The build recipe already replaces Perl build-time links with copy semantics; changing Archive::Tar's runtime symlink semantics would be a CPAN/runtime compatibility change, not needed for MPI build-tool consumption. |
| 2 | `../cpan/ExtUtils-Install/t/can_write_dir.t` | After `chmod 0555`, `_can_write_dir()` returned writable where the test expected not writable. | OHOS permission bits and `-w`/actual-write behavior diverge. The directory remains effectively writable although the mode looks read-only. | Build path already fixed by `0002-extutils-install-write-probe.patch`, which checks actual create/unlink ability. No further upstream-test patch is made because the test intentionally asserts POSIX permission-bit semantics that the device storage does not provide. |
| 3 | `../cpan/ExtUtils-Install/t/Install.t` | `link DummyHard.pm`, `symlink Dummy.pm`, and `DummyOrig.pm not writeable` failed. | Hardlink/symlink creation is denied, and chmod-based non-writable expectations do not hold on the storage. | Not fixed in Path A. The recipe's copy-link wrapper covers Perl's own build/install flow; preserving real hardlink/symlink behavior for ExtUtils runtime tests needs filesystem/platform support. |
| 4 | `../cpan/ExtUtils-Install/t/Packlist.t` | `write() should croak on open failure` produced no error after chmod read-only. | The test relies on chmod making a file unwritable. On this storage, writes can still succeed. | Not fixed in Path A. The install write-probe patches deliberately follow actual writeability, which is correct for packaging. |
| 5 | `../cpan/ExtUtils-MakeMaker/t/02-xsdynamic.t` | Test XS `.so` failed to load: `is_odd: symbol not found`. | Temporary ExtUtils::MakeMaker dynamic XS fixture exposes an OHOS dynamic-loader/export edge case for symbols shared between test XS objects. | Not fixed in Path A. It needs focused linker/loader investigation and is outside the `perl` build-tool acceptance path; normal package smoke tests for interpreter/core-module loading pass. |
| 6 | `../cpan/ExtUtils-MakeMaker/t/03-xsstatic.t` | Static XS fixture could not locate/load `XS::Other`; `is_odd.t` aborted. | ExtUtils::MakeMaker's static-extension test layout does not map the nested test XS module correctly under the OHOS build/run environment. | Not fixed in Path A. This is a secondary CPAN developer workflow, not required by Open MPI/MPICH configure-time perl use. |
| 7 | `../cpan/ExtUtils-MakeMaker/t/eu_command.t` | Six chmod mode checks returned modes such as `448`/`384` instead of `64`/`256`/`128`; `dos2unix` text comparison also failed. | The dominant failure is OHOS chmod/mode normalization. The `dos2unix` mismatch is a test-fixture text-normalization edge and is not tied to package installation. | Not fixed in Path A. Changing ExtUtils command behavior to fake POSIX mode bits would be unsafe for general Perl runtime behavior. |
| 8 | `../cpan/ExtUtils-MakeMaker/t/fixin.t` | Shebang rewrite tests returned empty output and one bad plan: expected `-w` switch/interpreter rewrite was absent. | The test exercises direct executable-script/shebang rewriting in temporary paths. This overlaps the same OHOS script-execution restrictions that require the recipe to invoke scripts through an explicit shell. | Not fixed in Path A. The recipe already shell-wraps configure/tool scripts; changing generic `fixin` behavior needs upstream/Test::Harness policy. |
| 9 | `../cpan/ExtUtils-MakeMaker/t/Mkbootstrap.t` | `should die given bad filename` did not produce `Unable to open dasboot.bs`. | The test expects a failed open path; OHOS permission/open behavior in the test directory did not match that expectation. | Not fixed in Path A. It is a test of error text under artificial bad-path permissions, not part of the build-tool consumption path. |
| 10 | `../cpan/ExtUtils-Manifest/t/Manifest.t` | Executable-bit check failed; `maniadd()` did not fail opening `MANIFEST`. | Executability and chmod/open-denial checks do not behave like POSIX file permissions on the storage. | Not fixed in Path A. Fixing would mean faking mode/open behavior in core modules, which is too broad. |
| 11 | `../cpan/File-Path/t/Path.t` | Symlink setup failed; many mkdir/chmod mode assertions all got mode `1513`; safe rmtree output differed. | The test relies on symlink support and exact chmod propagation for new directories; OHOS storage normalizes modes and restricts links. | Not fixed in Path A. `File::Path` general POSIX-permission compatibility needs platform support or upstream conditional skips. |
| 12 | `../cpan/File-Temp/t/tempfile.t` | `created tempfile with changed permissions` got mode `384` instead of `256`. | Chmod does not produce the requested restrictive mode. | Not fixed in Path A. Package build uses explicit build-local `TMPDIR`, but exact temp-file permission semantics remain platform-limited. |
| 13 | `../cpan/IO-Compress/t/109merge-deflate.t` | `InflateScan` constructor was undefined/failed; then `write` was called on an undefined object. | The IO::Compress Merge path depends on `Compress::Raw::Zlib::InflateScan`; this specific zlib scan/merge path failed despite broad IO-Compress coverage passing. | Not fixed in Path A. It requires a dedicated zlib/Compress::Raw::Zlib investigation and is not needed for configure-time perl use. |
| 14 | `../cpan/IO-Compress/t/109merge-gzip.t` | Same `InflateScan` constructor failure as the deflate merge test. | Same IO::Compress Merge/InflateScan runtime edge. | Not fixed in Path A for the same reason as #13. |
| 15 | `../cpan/IO-Compress/t/109merge-rawdeflate.t` | Same `InflateScan` constructor failure as the deflate merge test. | Same IO::Compress Merge/InflateScan runtime edge. | Not fixed in Path A for the same reason as #13. |
| 16 | `../cpan/IPC-SysV/t/ipcsysv.t` | `Bail out! SIGSYS caught` after the first test. | SysV IPC is detected at configure time but blocked or unavailable at runtime on the true device. | Fixed in this revision by excluding `IPC/SysV` from OHOS `noextensions`. A fresh upstream rerun should skip this file instead of running broken SysV IPC code. |
| 17 | `../cpan/Test-Harness/t/source_handler.t` | Direct exec of `source.sh` and `source_args.sh` failed with `Permission denied`. | The device rejects direct execution of `.sh` test scripts from the test tree. | Not fixed in Path A. The recipe invokes configure/build scripts through an explicit shell; changing Test::Harness's generic executable handler would alter upstream semantics. |
| 18 | `../cpan/Time-Piece/t/02core.t` | `TZ=EST5` produced offset `-14400` and `EDT`, expected `-18000` and `EST`. | OHOS timezone/DST interpretation differs from the test's fixed EST expectation. | Not fixed in Path A. This is locale/timezone runtime compatibility, not needed for the build-tool use case. |
| 19 | `../dist/IO/t/io_unix.t` | Unix socket path warnings show 117/127 byte paths over the 108 byte `sockaddr_un` limit; final bind hit `Address in use`. | The upstream harness run directory makes generated AF_UNIX paths too long and truncation causes collision. | Test-environment fixable with a shorter `TMPDIR`/run path, but not changed in the package PR. The recipe already sets build-local `TMPDIR`; upstream harness reproduction should use a short device path if this file is retested. |
| 20 | `../dist/PathTools/t/cwd.t` | `Cwd::abs_path` stayed at `linktest`, `fast_abs_path` was undef, and expected errno was 13 but got 2. | Symlink path resolution and permission/error-code semantics differ on the storage. | Not fixed in Path A. Requires platform symlink semantics or upstream conditional behavior. |
| 21 | `../dist/PathTools/t/tmpdir.t` | `tmpdir() always returns an absolute path` failed when the test set relative `TMPDIR`. | The test mutates `TMPDIR` to relative paths; File::Spec accepted/returned a relative candidate under the current environment. | Test-environment fixable by using absolute `TMPDIR`, but not a package change. The recipe uses absolute build-local temp paths. |
| 22 | `../dist/Time-HiRes/t/itimer.t` | `VTALRM` interrupted the process and `time left should be zero` was nonzero. | Virtual interval timer/signal delivery differs from upstream expectations. | Not fixed in Path A. Needs platform signal/timer support or upstream skip logic. |
| 23 | `../ext/File-Find/t/find.t` | Initial symlink creation failed; multiple `follow`/`follow_fast` traversals failed; dangling symlink setup died. | File::Find tests require creating and traversing symlinks. | Not fixed in Path A. Requires filesystem symlink support. |
| 24 | `../ext/File-Find/t/taint.t` | Symlink creation failed and symlink traversal missed `fsl`. | Same symlink restriction as File::Find, under taint mode. | Not fixed in Path A. Requires filesystem symlink support. |
| 25 | `../ext/File-Glob/t/basic.t` | `GLOB_ERROR is not 0` failed after creating a mode-0 directory. | The test expects unreadable-directory globbing to set an error; chmod mode 0 does not deny access as expected. | Not fixed in Path A. This is a permission-mode semantic gap. |
| 26 | `../ext/POSIX/t/sigaction.t` | `SIGRTMIN handler works` got undef. | Real-time signal delivery/handler behavior does not match upstream POSIX test assumptions. | Not fixed in Path A. Needs platform signal support or upstream conditional skip. |
| 27 | `../ext/POSIX/t/termios.t` | Four checks expected `ENOTTY` 25 but got `EACCES` 13. | Terminal ioctl calls on the device return access-denied instead of not-a-tty. | Not fixed in Path A. This is platform errno behavior. |
| 28 | `../ext/SDBM_File/t/sdbm.t` | DBM permission check got mode `432`, expected `416`. | DBM test depends on exact chmod result for data files. | Not fixed in Path A. The recipe already disables external DBM libraries; SDBM's exact permission-mode test remains platform-limited. |
| 29 | `../lib/AnyDBM_File.t` | `File permissions` failed. | Same chmod/stat mode mismatch as SDBM/DBM permission tests. | Not fixed in Path A. Permission-bit exactness is not reliable on the target storage. |
| 30 | `../lib/File/Copy.t` | `link("file-$$", "hardlink-$$")` died with `Operation not permitted`. | Hardlink creation is denied. | Not fixed in Path A. The recipe uses copy semantics for Perl's build-time hardlinks; disabling or emulating Perl's runtime `link()` globally would be too broad. |
| 31 | `../lib/warnings.t` | Three failures included `Can't set $0 with prctl(): Invalid argument`; one child was manually terminated. | Perl configured `HAS_PRCTL_SET_NAME`, but OHOS rejects some real `$0` updates. | Fixed in this revision with `-Ud_prctl_set_name`. A fresh upstream rerun should remove these `$0`/prctl failures. |
| 32 | `io/fs.t` | Hardlink tests failed; chmod/link-count/unlink/mode checks differed. | Hardlink and chmod semantics differ from POSIX assumptions. | Not fixed in Path A. Requires filesystem behavior not provided by the test storage. |
| 33 | `io/open.t` | FD inheritance check expected `0`, got `1` for `open(F, "+<&=3")` after exec. | File-descriptor close-on-exec/inheritance behavior differs for this Perl open mode under OHOS. | Not fixed in Path A. Needs focused core Perl/OHOS fd semantics work; not required by MPI configure use. |
| 34 | `io/sem.t` | `semctl not implemented`; process exited 22. | SysV semaphore APIs are detectable but not usable. | Fixed in this revision by excluding `IPC/SysV` on OHOS. `PERL_CORE` tests should skip when the extension is absent. |
| 35 | `op/filetest.t` | `-w` for directory returned false; symlink-related `-l *foo` failed after `ln` permission errors. | File test operators expose the same writable and symlink semantic gaps. | Not fixed in Path A. The build recipe uses actual write probes where needed instead of changing global filetest behavior. |
| 36 | `op/leaky-magic.t` | Manual `TERM` after `Can't set $0 with prctl(): Invalid argument`. | Same `$0`/`PR_SET_NAME` misconfiguration. | Fixed in this revision with `-Ud_prctl_set_name`. |
| 37 | `op/lex.t` | Expected malformed UTF-8 diagnostic was replaced by `Can't set $0 with prctl(): Invalid argument`. | Same `$0`/`PR_SET_NAME` misconfiguration in a BEGIN block. | Fixed in this revision with `-Ud_prctl_set_name`. |
| 38 | `op/magic.t` | Manual `TERM` after `$0`/prctl failure; `ps` also reported unsupported option `h`. | Primary blocker is `$0`/`PR_SET_NAME`; a secondary process-listing expectation may remain because device `ps` differs. | Partially fixed in this revision with `-Ud_prctl_set_name`. A fresh targeted rerun is needed to see whether the `ps` option difference remains. |
| 39 | `op/require_errors.t` | Permission-denied module tests produced empty `$@` instead of `Can't locate ...`. | The test switches euid and expects open failure for an unreadable module; OHOS permission behavior did not produce the same error path. | Not fixed in Path A. Requires permission/euid semantics alignment or upstream conditional skip. |
| 40 | `op/stat.t` | Hardlink, link count, `-r/-w/-x`, symlink, `-l`, and owner checks failed; symlink died with `Permission denied`. | Hardlink/symlink and file permission/stat semantics differ from POSIX expectations. | Not fixed in Path A. Runtime stat/link compatibility needs platform support. |
| 41 | `op/taint.t` | Harness aborted after symlink failure (`Permission denied`). | Taint tests reached filesystem cases that require symlink creation. | Not fixed in Path A. Requires filesystem symlink support. |
| 42 | `porting/globvar.t` | `PL_current_context` was listed for export but never defined. | Perl porting symbol audit detects an internal export-table/config mismatch for this build. | Not fixed in Path A. It is a porting-maintainer check and does not affect the packaged interpreter smoke or MPI build-tool use; needs separate upstream/core export review. |
| 43 | `run/locale.t` | Illegal locale environment did not emit the expected `Falling back to the standard locale` message. | OHOS locale startup/fallback diagnostics differ from upstream expectations, with locale support intentionally minimized in the recipe. | Not fixed in Path A. This is locale diagnostics compatibility, not needed for configure-time perl. |
| 44 | `run/todo.t` | Harness reports `TODO passed: 3-4`. | This is not a functional runtime failure; upstream TODO tests unexpectedly passed, which still makes the harness non-clean. | No code fix. Record as upstream harness accounting only. |

## Expected effect of this revision

The current recipe changes are expected to close or convert to skips the following failed files on a fresh true-device upstream rerun:

- `../cpan/IPC-SysV/t/ipcsysv.t`
- `io/sem.t`
- `../lib/warnings.t`
- `op/leaky-magic.t`
- `op/lex.t`
- `op/magic.t` for the `$0`/prctl blocker; `ps` behavior may still need review.

The remaining failures are intentionally not patched in this Path A package revision because they require platform filesystem/POSIX semantics, upstream conditional skips, or broader runtime compatibility work beyond the immediate `perl` build-tool dependency required by `open-mpi/5.0.10` and `mpich/4.0.3`.

The follow-up true-device Conan rerun after these two recipe fixes passed L0, including the software-level `commands.json` check, completed `Configure`, `make`, and `package()`, and created package revision `d8f9b5d50161ac009ed647586fab2d9a`. It then failed only in `test_package` because the device work copy had CRLF line endings in `test_perl.sh`; after syncing the LF-normalized script, the generated package smoke passed. A fresh full Conan rerun is intentionally paused after that failed build per user instruction.
