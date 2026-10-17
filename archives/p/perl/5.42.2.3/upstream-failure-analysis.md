# Perl 5.42.2 complete upstream test report (perl/5.42.2.3)

The Conan package version is `5.42.2.3`; the upstream source and runtime version are `5.42.2`. This report documents the fresh clean-source run performed on 2026-09-03 on a true HarmonyOS aarch64 device (same recipe lineage as the validated `5.42.2.1`; only the Conan `version` field differs).

## Complete post-fix run

The complete upstream harness was rerun on the rebuilt OHOS aarch64 tree:

```sh
cd <conan build dir of perl/5.42.2.3>
TEST_JOBS=4 HARNESS_NOTTY=1 TMPDIR=<short writable path> make test_harness_notty
```

| Metric | Result |
|---|---:|
| Test programs processed | 2,902 |
| Assertions executed | 1,349,481 |
| Passing test programs | 2,714 |
| Failing test programs | 25 |
| Programs skipped by the upstream harness | 163 |
| Wall-clock time | 472 seconds |
| Manually terminated hangs | 0 |
| Harness result | FAIL |

`2,714` is calculated as `2,902 - 25 - 163`. Skipped programs are not counted as passes. A global assertion pass percentage is not claimed because TAP syntax failures can have incomplete or reordered plans. Full raw logs: `w3-5.42.2.3/harness-5.42.2.3.log`; per-file minimal-reproduction TAP and platform probes: `qc-logs/failed-details/` and `qc-logs/evidence/` (25 failure files are identical to the previously validated same-lineage run on the same device).

## Fixed regressions

| Test program | Before | After | Fix |
|---|---|---|---|
| `op/leaky-magic.t` | Hung after 46/71 | PASS | Disable unusable OHOS `prctl` process-name support at Configure time. |
| `op/lex.t` | `$0`/`prctl` error | PASS | Same Configure correction. |
| `op/taint.t` | Child hung; incomplete plan | PASS | Same Configure correction. |
| `lib/warnings.t` | Three failures and a hung child | PASS | Same Configure correction. |
| `cpan/ExtUtils-MakeMaker/t/02-xsdynamic.t` | 1/90 failed: dependent XS could not resolve `is_odd` | PASS 90/90 | Add OHOS to the existing explicit shared-library dependency path because its loader does not expose producer symbols through `RTLD_GLOBAL`. |
| `dist/threads/t/join.t` | Incomplete plan in the earlier contaminated run | PASS | Passed in the clean rebuilt tree; no source change was needed. |

`op/magic.t` no longer hangs. It retains one failure: assertion 203 expects `ps` to show an argv-based `$0` update, but OHOS `ps` continues to show the executable path after unusable `prctl` support is disabled.

## Upstream test-source modification

Patch `0004-extutils-xs-needed-on-ohos.patch` changes only the platform dispatch table in `cpan/ExtUtils-MakeMaker/t/lib/MakeMaker/Test/Setup/XS.pm`. It adds OHOS to the same explicit `.so` dependency strategy already used for Android. It does not remove an assertion, change an expected value, or mark a failure as skipped. The resulting dependent XS module contains a real `DT_NEEDED` edge and the original 90 assertions execute unchanged.

## All remaining failing test programs

| # | Test program | Observed failure | Reason / current classification |
|---:|---|---|---|
| 1 | `io/fs.t` | 11/61 failed | Worker filesystem lacks expected hard-link, link-count, chmod and unlink semantics. |
| 2 | `op/filetest.t` | 1/436 failed | Effective writability after chmod differs from POSIX expectation. |
| 3 | `op/magic.t` | 1/208 failed | OHOS `ps` does not expose argv-based `$0` process-title changes; no hang remains. |
| 4 | `op/require_errors.t` | TAP sequence errors | chmod does not make the fixture unreadable, so expected require errors are absent. |
| 5 | `op/stat.t` | 9/111 failed | Hard links, mode, ownership/device metadata and unreadable-file behavior differ. |
| 6 | `porting/globvar.t` | 1/4 failed | Porting-only check expects an internal symbol absent from this threaded configuration (clang emulated-TLS naming). |
| 7 | `run/locale.t` | 1/45 failed | Invalid locale environment does not emit the expected fallback warning. |
| 8 | `cpan/ExtUtils-Install/t/Install.t` | 2/62 failed | Hard-link creation and chmod-based non-writable checks differ. |
| 9 | `cpan/ExtUtils-MakeMaker/t/eu_command.t` | 6/40 failed | Requested chmod modes are normalized rather than preserved exactly. |
| 10 | `cpan/ExtUtils-Manifest/t/Manifest.t` | 1/101 failed | Executable-bit propagation differs on the worker filesystem. |
| 11 | `cpan/File-Path/t/Path.t` | 18/167 failed | New directory modes do not preserve exact requested chmod values. |
| 12 | `cpan/File-Temp/t/tempfile.t` | 1/30 failed | Temporary-file permission mode differs from the exact expectation. |
| 13 | `cpan/Time-Piece/t/02core.t` | 2/100 failed | `TZ=EST5` resolves to daylight offset/name instead of fixed EST expectation. |
| 14 | `dist/IO/t/io_unix.t` | 0 tests; exited 1 | AF_UNIX bind is blocked with `Operation not permitted` by the sandbox (seccomp); a short TMPDIR does not change this on this device. |
| 15 | `dist/PathTools/t/cwd.t` | 1/35 failed | Failure-path errno differs from expected `EACCES`. |
| 16 | `dist/Time-HiRes/t/itimer.t` | VTALRM; 1/2 failed | Virtual interval-timer delivery/remaining-time semantics differ. |
| 17 | `ext/File-Glob/t/basic.t` | 1/56 failed | `GLOB_ERROR` remains zero for an error fixture. |
| 18 | `ext/POSIX/t/sigaction.t` | 1/36 failed | Real-time signal handler does not run as expected. |
| 19 | `ext/POSIX/t/termios.t` | 4/1571 failed | Invalid terminal operations do not set expected `ENOTTY`. |
| 20 | `ext/SDBM_File/t/sdbm.t` | 1/133 failed | Database file permission mode differs. |
| 21 | `lib/AnyDBM_File.t` | 1/12 failed | Database file permission assertion differs. |
| 22 | `lib/File/Copy.t` | Exited without plan | Metadata-preserving copy is rejected with `Operation not permitted`. |
| 23 | `lib/perl5db.t` | 1/8; no plan | Debugger child does not produce expected `db.out` (chmod 0644 normalized to 0660 makes `.perldb` look group-writable). |
| 24 | `lib/locale_threads.t` | 1/2 failed | Threaded locale stress reports a failure under OHOS locale behavior. |
| 25 | `dist/IO/t/cachepropagate-unix.t` | 1/1 failed | AF_UNIX socket creation is blocked by the sandbox (seccomp EPERM). |

## All upstream harness skips

The harness explicitly skipped 163 programs; none are counted as passes.

| Category | Count | Why these programs could not run |
|---|---:|---|
| Author, release, development, maintenance, POD or Git-checkout-only | 41 | Enabled only under author/release flags, development/debug builds or a Git checkout. |
| Missing optional dependencies | 32 | Optional Test::Pod, Math::BigInt backends, DBM variants, Tk, AnyEvent, POE, JSON::MaybeXS, Test::LeakTrace and similar tools are absent. |
| Upstream-inapplicable, removed, unsupported or unimplemented | 23 | Targets removed features, unfinished tests or upstream-declared unsupported paths. |
| Resource-intensive tests disabled by upstream defaults | 17 | Lengthy tests and roughly 4–10 GiB memory cases require explicit opt-in and are unsuitable for the shared worker. |
| Other operating-system or architecture tests | 14 | Windows, Darwin, BeOS, Cygwin, OS/2, VMS, NW5 or 32-bit specific. |
| Missing build or platform capability | 12 | Requires SysV IPC, DTrace, DEBUGGING/PERL_RC_STACK, root, O_EXLOCK, a specific locale or another unavailable capability. |
| External network or interactive environment | 12 | Requires configured services, external network, special loopback behavior or an interactive terminal. |
| Other explicit upstream skips | 12 | Configuration-dependent portability decisions and test-specific `skip_all`. |
| **Total** | **163** | |

## Acceptance scope

The full upstream suite is still not represented as passing. The repaired package now builds without process-name hangs, passes the dependent dynamic XS test, executes the six Conan consumer assertions, and verifies `.codesign` on every delivered Perl/XS ELF. Remaining failures are documented rather than hidden.
