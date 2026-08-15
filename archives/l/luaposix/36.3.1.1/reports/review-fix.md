# Review fix and upstream test report

- Date: 2026-08-13
- Issue: #2117
- Pull request: #5204
- Package: `luaposix/36.3.1.1`
- Fix commit: `522e0660105a0b8595b0e311c222295d4a0add0f`

## Root cause

The recipe invoked `build-aux/luke` without the `package` and `version`
arguments used by the upstream rockspec. The lukefile default for `version` is
`$USER`, so an OHOS build by `currentUser` embedded this incorrect value:

```text
posix for Lua 5.4 / luaposix currentUser
```

The recipe now passes `package=luaposix version=36.3`. The consumer test adds a
sixth assertion that `posix.version` ends in upstream version `36.3`.

## Targeted shadow CI

Commit `522e0660105a0b8595b0e311c222295d4a0add0f` passed the single-package
OHOS/aarch64 shadow run:

- L0: pass
- L1: pass, all six `test_package` assertions executed
- L2: skip, library package has no `bin/` directory
- L4: pass, patches clean
- L5: pass, `lib/` has content
- Package summary: 1/1 successful, 100%

Run root:

```text
/storage/Users/currentUser/ohpc-ci-shadow/runs/522e066010-20260813T093420Z-run-47294
```

## Upstream specl execution

The device harness used official Lua 5.4.8, specl 14.1.8, lyaml 6.2.8,
LuaMacro, optparse, lua-stdlib 41.2.1, std._debug 1.0.1, and typecheck 3.0
sources, plus published lpeg 1.1.0 and libyaml 0.2.5 packages. Version 14.1.8
is the newest specl release whose `badargs.diagnose(fn, declaration)` API
matches luaposix v36.3 while officially allowing Lua 5.4. Specl 14.1.9 and
14.1.10 reverse those arguments and cannot execute this upstream release.

The harness handled OHOS `TMPDIR` and mapped the known `unix` build object
directory. It did not change an upstream YAML expectation or a package
artifact. Each spec file ran in a separate process so a signal in an
unsupported module could not hide the results of later files.

### Full 26-file diagnostic run

All 26 discovered upstream files were launched. Sixteen completed successfully
and ten failed or terminated while exercising facilities whose assumptions do
not hold on the test device. This diagnostic run intentionally exits nonzero;
it is evidence of full execution, not a 100% pass claim.

Observed failure classes:

- the application sandbox rejects or changes hard links, symbolic links,
  FIFOs, permission-bit changes, unreadable-directory assumptions, and the
  upstream `/var/tmp` path assumption;
- `currentUser` has no matching passwd database record, so specs deriving
  `ids` or home-directory fields from `getpwnam()` cannot continue;
- pseudo-terminal setup returns no master descriptor;
- `%Z` does not emit an arbitrary `tm_zone` value supplied by the test;
- SysV message-queue calls terminate the process with signal 31;
- the remaining assertions expose errno, `utime`, and filesystem timestamp
  semantics that differ from the Linux expectations.

The affected files are `posix_compat_spec.yaml`,
`posix_deprecated_spec.yaml`, `posix_dirent_spec.yaml`,
`posix_glob_spec.yaml`, `posix_spec.yaml`, `posix_stdlib_spec.yaml`,
`posix_sys_msg_spec.yaml`, `posix_sys_stat_spec.yaml`,
`posix_time_spec.yaml`, and `posix_unistd_spec.yaml`.

Full diagnostic run root:

```text
/storage/Users/currentUser/ohos-test-runs/currentUser-luaposix-upstream-specl-1418-v5-044c17-20260813-215433-14531
```

### OHOS-runnable upstream subset

The 16 files that completed in the diagnostic run were executed again as a
fixed subset. The runner exited zero with these results:

- discovered upstream files: 26
- executed subset: 16 files (61.54% file coverage)
- result: 16 passed, 0 failed
- expectations: 1147 passed, 5 upstream pending, 0 failed
- executed-expectation pass rate: 100%
- stderr: empty

The subset covers `lposix`, `ctype`, `fcntl`, `fnmatch`, `grp`, `pwd`,
`signal`, `stdio`, `sys.resource`, `sys.socket`, `sys.statvfs`, `sys.time`,
`sys.times`, `sys.utsname`, `syslog`, and `version`.

Runnable-subset run root:

```text
/storage/Users/currentUser/ohos-test-runs/currentUser-luaposix-upstream-specl-runnable16-044c17-20260813-220456-18727
```

The seven test-only Lua dependencies are absent from the OHPCD Conan remote.
Per the one-library-per-PR rule they are not vendored or added as production
dependencies here; the reproducible true-device evidence is kept separate
from the six-assertion package-consumer smoke test.

## Infrastructure incident

One formal PR CI attempt failed before repository checkout because the Worker
SSH bridge was refused (`connection lost before ready`, errno 111). This is an
infrastructure failure and contains no recipe execution evidence.
