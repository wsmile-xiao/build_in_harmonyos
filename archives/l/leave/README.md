# leave

A tiny "remind me when it's time to leave" command-line utility from the BSD
base systems (`usr.bin/leave`, original 4.4BSD code). Given a time it forks a
background child that warns you five minutes before, one minute before, and
then every minute for ten minutes.

- Homepage: https://man.netbsd.org/leave.1
- License: BSD-3-Clause (Copyright (c) 1980, 1988, 1993 The Regents of the
  University of California); the notice lives in the `leave.c` header as
  upstream ships no separate license file
- Build system: BSD make upstream (`PROG=leave` + `.include <bsd.prog.mk>`);
  on OHOS the single translation unit `leave.c` is compiled directly with the
  Conan-provided clang
- Dependencies: none (libc only)

## OHOS adaptation notes

- The upstream `Makefile` is a *BSD make* fragment that includes
  `bsd.prog.mk` — a file of the BSD build framework that does not exist
  outside a BSD source tree. It is therefore unusable on OHOS/CI, and the
  recipe compiles `leave.c` directly instead of going through `make`.
- `patches/0001-leave.c.patch` (portability, no `__OHOS__`):
  `#ifndef` fallbacks for the NetBSD `__COPYRIGHT`/`__RCSID` macros (absent
  from musl's `<sys/cdefs.h>`), a `getprogname(3)` fallback compiled only on
  non-BSD platforms (OHOS musl exports `__progname` but has no `getprogname`),
  and the portable `unsigned int` spelling in place of the BSD `u_int` type
  (musl only exposes `u_int` behind feature macros, and this sysroot's
  `<sys/param.h>` does not pull in `<sys/types.h>`).
- The executable links only against libc (`NEEDED libc.so`); no system-name
  library is involved (R26 trivially satisfied).
- `R38`: this package installs `bin/leave`, so the software-level
  `commands.json` declares it as `type: "tool"` for `1.12`.

## Tests

Upstream ships **no test suite** — the 1.12 archive contains exactly three
files (`Makefile`, `leave.1`, `leave.c`) with no tests, no test target and no
CI config (see `1.12/test_package/MANIFEST.yml` for the full census, N=0).
The adaptation therefore adds its own `test_package`:

- `test_leave.sh` — generic consumer tests: three invalid-argument cases
  (usage + exit 1), the no-argument + EOF prompt path (exit 0), and the valid
  `+6` scheduling path (parent exit 0; the forked nagging child is killed).
- `ohos_specific_test.py` — HarmonyOS-specific suite (R53, fail closed): ELF64
  little-endian AArch64 identity, the `/lib/ld-musl-aarch64.so.1` interpreter,
  no RPATH/RUNPATH, plus real execution of the packaged binary on the OHOS PC
  asserting the invalid-argument exit code, the no-argument prompt and the
  `+6` alarm announcement with child reaping.

Because leave's normal behaviour is to *wait* for the requested time, every
test uses only immediately-terminating paths (invalid arguments, EOF) or kills
the forked child, so nothing hangs.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.12    | built  | NetBSD/FreeBSD `usr.bin/leave` 1.12; source from the pristine upstream `.orig` archive (no first-party release exists) |
