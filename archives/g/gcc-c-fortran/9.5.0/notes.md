# gcc-c-fortran 9.5.0 HarmonyOS adaptation notes

## Current state

GCC 9.5.0 with C and Fortran frontends for HarmonyOS AArch64. Builds the
gfortran driver, f951 compiler, libgcc and libgfortran runtime. The recipe
is derived from the validated `gcc/9.5.0` C-only package with Fortran
support added through the same source-transform infrastructure.

Status: built (W3 local CI passed, gfortran.dg subset 4/4, test_package gfortran PASSED).

## libgfortran and libquadmath decision (R26 / upstream configure behavior)

The upstream GCC 9.5 configure system detects libquadmath at libgfortran
configure time. If libquadmath is present, gfortran supports `REAL(16)`
(quad precision) through `__float128`. If absent, `REAL(16)` is unavailable
but all standard IEEE types (`REAL(4)`, `REAL(8)`, `COMPLEX(4)`, `COMPLEX(8)`)
remain fully supported.

Similarly, `libbacktrace` is an optional runtime library that provides
enhanced error backtrace support in libgfortran. If absent, gfortran
degrades gracefully to basic error messages without stack trace.

This recipe keeps `--disable-libquadmath` and `--disable-libgomp` matching
the `gcc/9.5.0` C-only baseline. Rationale:
- `libquadmath` is a small library but adds build complexity and a second
  target library to build/install/sign; the base C recipe validated without
  it, and REAL(16) is rarely needed in scientific Fortran codes.
- `libgomp` (OpenMP) requires POSIX threads; OHOS musl lacks `pthread_cancel`
  and the recipe uses `--disable-threads`. OpenMP-dependent codes cannot
  link but basic Fortran programs work correctly.

### ⚠️ libbacktrace must stay ENABLED (fix, 2026-09-20)

An earlier draft disabled libbacktrace (`--disable-libbacktrace`) because a
first build attempt hit `configure-target-libbacktrace: C compiler cannot
create executables`. That was the wrong fix: in GCC 9.5 the **host**
`cc1`/`f951` frontends link `../libbacktrace/.libs/libbacktrace.a`
unconditionally (see `gcc/Makefile.in` `LIBDEPS`/`LIBS`), so disabling it
breaks `all-gcc` with:

```
make[1]: *** No rule to make target '../libbacktrace/.libs/libbacktrace.a',
needed by 'cc1-checksum.c'.  Stop.
```

The real fix has two parts:
1. Keep libbacktrace enabled (remove `--disable-libbacktrace`).
2. Give the in-tree `xgcc-sign` target compiler wrapper `-B<sysroot>/usr/lib/
   <triplet>/` so `configure-target-libbacktrace` (and libgfortran) link
   probes find crt1.o/crti.o/crtn.o and succeed. The packaged driver wrapper
   already injects this path; the in-tree wrapper now does the same.

`package()` therefore installs `install-target-libbacktrace` as well so the
optional error-traceback support in libgfortran is preserved.

If quad precision support is later required, enable libquadmath by removing
`--disable-libquadmath` and adding `make all-target-libquadmath` and
`install-target-libquadmath` to the build/package targets.

### ⚠️ fixincludes must be skipped on OHOS (fix, 2026-09-20)

The GCC `stmp-fixinc` rule (fixincludes) runs `fixinc.sh` inside a subshell
that `cd`s between build directories. On HMDFS, `getcwd()` fails there with
`chdir: error retrieving current directory: getcwd: cannot access parent
directories: Not a tty` and make aborts `stmp-fixinc` during
`make -C gcc selftest` (and later `make install-gcc`).

OHOS musl headers are already clean and need no fixing, so the recipe
pre-stamps `gcc/stmp-fixinc` and creates an essentially empty
`include-fixed/` directory (with `syslimits.h`) before running selftest.
This makes make skip `fixinc.sh` deterministically on both the local worker
and CI, and keeps `install-headers` / `install-mkheaders` working.

### ⚠️ gfortran.dg subset uses -x f95, not -x fortran (fix, 2026-09-21)

The first full W3 build reached selftest (stmp-fixinc fix verified: no more
HMDFS getcwd crash) and then the fortran test subset failed with:

```
xgcc: error: language fortran not recognized
upstream gfortran.dg subset: 0/4 passed
```

GCC's driver only recognises the f77/f95 language names; `-x fortran` is not
a valid selectable language.  The test invocation now uses `-x f95`, which
selects the freshly built f951 and the gfortran link spec.

## Build flow

1. Download GCC 9.5.0 + GMP 6.1.0 / MPFR 3.1.4 / MPC 1.0.3 (in-tree).
2. Apply OHOS source transforms (config.sub, musl, umask, config.gcc).
3. Configure `--enable-languages=c,fortran` with OHOS sysroot.
4. Build `all-gcc` (host tools: cc1, f951, gcc, gfortran, collect2).
5. Sign ELF host tools, build `xgcc-sign` wrapper.
6. Build `all-target-libgcc` using `xgcc-sign` as `CC_FOR_TARGET`.
7. Build `all-target-libgfortran` (depends on libgcc).
8. Run GCC selftest + gfortran.dg smoke subset (upstream test set).
9. `make install-gcc install-target-libgcc install-target-libgfortran`.
10. Install relocatable driver wrappers for gcc and gfortran.

## Resume commands

```sh
python3 scripts/ohc-run.py conan-verify gcc-c-fortran 9.5.0
CI_PACKAGES="archives/g/gcc-c-fortran/9.5.0" zsh ci/conan/build_and_test.sh
```

### ⚠️ libgfortran link search needs .libs subdirectory (fix, 2026-09-21)

The second full W3 build compiled the fortran test sources with `-x f95`
(language recognised) but every link failed with:

```
undefined reference to `_gfortran_set_args'
undefined reference to `_gfortran_set_options'
```

libgfortran is built with libtool, so `libgfortran.a` lands in
`aarch64-linux-ohos/libgfortran/.libs/`, not the directory root.  The test
driver's `-B` search path must point at `.libs/` for the gfortran link spec's
`-lgfortran` to resolve.

### ⚠️ xgcc driver does not auto-link -lgfortran (fix, 2026-09-21)

Even with the correct `.libs/` search path, the third full W3 build still
failed to link every fortran test with undefined references to
`_gfortran_set_args`/`_gfortran_set_options`/`_gfortran_stop_numeric` etc.
`libgfortran.a` does contain those symbols; the problem is that the generic
`xgcc` driver (unlike the `gfortran` driver) does NOT add `-lgfortran` to the
link line when invoked with `-x f95`.  The recipe now passes
`-L<libgfortran/.libs> -lgfortran` explicitly at link time.

### ⚠️ package() install needs CC_FOR_TARGET for target libs (fix, 2026-09-21)

Rebuild #4 passed the fortran smoke tests (`gfortran.dg subset: 4/4 passed`
— the `-lgfortran` fix works) but then failed in `package()`:

```
In file included from .../gcc/include-fixed/stdio.h:24,
                 from .../libgfortran/libgfortran.h:42,
                 from .../libgfortran/caf/libcaf.h:32,
                 from .../libgfortran/caf/single.c:26:
sysroot/usr/include/stdint.h:20:10: fatal error: bits/alltypes.h: No such file
```

`make install-target-libgfortran` recompiles `libgfortran/caf/single.c`
(DESTDIR install path), but the plain `make install-...` did not pass
`CC_FOR_TARGET`, so the default in-tree `xgcc` (without the
`-isystem sysroot/usr/include/<triplet>/` argument) was used and could not
find the musl `bits/alltypes.h` in the OHOS sysroot target include dir.

Fix: `build()` stores the signed `xgcc-sign` wrapper as `self._target_cc`,
and `package()` appends `CC_FOR_TARGET=<wrapper>` to the install command.

### ⚠️ Wrapper shebangs must use bash, not /bin/sh (mksh SIGCHLD race) (fix, 2026-09-22)

W3 local CI stalled twice on the OHOS worker: a `sh clang-sign -c out_str.c`
process hung in `do_rt_sigsuspend` forever even though the object file had
already been produced.  OpenHarmony's `/bin/sh` is mksh, which loses SIGCHLD
in a race when waiting on the forked clang child; make then waits forever and
the whole `make all-gcc` tree deadlocks (observed twice, 2026-09-22).

Fix: both generated wrapper scripts (`_compiler_wrapper_text` and the
installed gcc/gfortran driver wrapper) now start with
`#!/data/service/hnp/bin/bash` instead of `#!/bin/sh`.  The system bash
(used already for `_run_with_unlimited_stack`) does not exhibit the SIGCHLD
loss, so compilation cannot deadlock on the wrapper wait.

## Final status

- status: built (W3 local CI passed, .ci-result.json exit_code=0, 2026-09-22)
- Latest local validation: passed (gfortran.dg subset 4/4, test_package gfortran PASSED)
- ohos_ci: pending (official CI to run after PR merge)
---

**编译结束**: 2026-09-22 22:31
**最终状态**: built
