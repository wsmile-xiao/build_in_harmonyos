# crack 5.0a HarmonyOS PC adaptation notes

## Summary

- Fresh adaptation of `crack/5.0a` (platform task #6889), the classic Unix
  password cracker by Alec Muffett (1991-1996). Source taken from the Debian
  archive (`crack_5.0a.orig.tar.gz`, packaging revision 5.0a-20).
- 1996 K&R-era C code; built with clang 15 using `-std=gnu89
  -Wno-int-conversion` to restore the legacy implicit-conversion semantics
  the code was written against.
- No configure script exists (pre-autotools project). The upstream `Crack`
  driver script wraps a hand-rolled Makefile tree; this recipe drives the
  same two stages directly:
  1. `make -C src/lib` → `run/bin/libc5.a`
  2. `make -C src/util ... stdlib-cracker dictfilt kickdict` →
     `run/bin/{cracker,dawg,xdawg,dictfilt,kickdict}`
- Uses the `stdlib-cracker` backend (libc `crypt(3)`), so the bundled
  `libdes`/`ufc-crypt` alternative crypt backends are not built and no
  external dependency is required.

## Build details

| Item | Value |
|---|---|
| Build system | hand-rolled Makefile (no configure) |
| Compiler | clang 15 (aarch64 OHOS cross) |
| Key CFLAGS | `-std=gnu89 -Wno-int-conversion -O2` + `-DUSE_STRING_H -DUSE_STDLIB_H -DUSE_SIGNAL_H -DUSE_SYS_TYPES_H -DUSE_UNISTD_H -DUSE_PWD_H` |
| Dependencies | none (libc crypt only) |
| Patches | none required（libdes TERMIOS 开关同样走编译参数，无源码补丁） |

### K&R vs modern clang notes

- `src/util/cracker.c` defines `Logger(key, fmt, a..f)` K&R-style with
  `char *` variadic stand-ins, then passes `int`/`long`/`pid_t` values;
  clang 15 makes these hard `-Wint-conversion` errors in modern dialects.
  `-std=gnu89` alone does not suppress them (they are errors under gnu89
  too in clang 15), `-Wno-int-conversion` downgrades them.
- Old-style function definitions without prototypes produce only
  deprecation warnings; they compile fine.
- `make` requires the output dir `run/bin` to exist before `ar rv`.

## Testing

- Upstream registers **exactly one** test target: `src/libdes/Makefile`
  line 77 `test: all` -> `./destest` (Eric Young libdes DES algorithm
  self-test: ecb/ede-cbc/pcbc/cfb/ofb/cbc_cksum/quad_cksum/alignment/
  fast crypt). Root, src/lib, src/util and extra Makefiles carry no
  test targets. Upstream registered test count: **N=1**.
- The recipe builds src/libdes + destest in build() Stage 4
  (`-DTERMIOS` replacing legacy `-DTERMIO`, since musl has no termio.h)
  and runs `./destest` — passes on OHOS aarch64: 14 case groups,
  zero error lines, exit 0.
- Note: the delivered `cracker` still uses the stdlib-cracker backend
  (libc crypt(3)); libdes is built solely to exercise the upstream test.
- Per platform rules, `test_package` carries HarmonyOS-specific tests:
  1. **dawg/xdawg roundtrip** — pack a known wordlist into the DAWG
     dictionary format and unpack it back; all words must survive.
  2. **cracker full run** — build dictionary groups via
     `scripts/mkdictgrps` (dict/1..3 sources, exactly like the upstream
     `Crack` driver), feed a `D:` SPF line whose ciphertext is
     `crypt("123456", "ab") = ab01FAX.bQRSU`, and require the cracker to
     report `G:...:123456`. Verified working by hand before packaging
     (guess observed at dictionary rule `dgrp=1 rules.fast ':'`).

## Verification plan

- `conan create archives/c/crack/5.0a --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default --build=missing`
---

**编译结束**: 2026-09-11 03:51
**最终状态**: published
