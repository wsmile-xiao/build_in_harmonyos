# avr-gcc-bootstrap 14.2.0 adaptation notes

Issue: #2245

## W0

- Required Conan build dependency: avr-binutils/2.43.1 from issue #2244.
- Runtime dependencies: OHOS base system only.
- GCC-required build sources are vendored at the exact versions selected by
  GCC 14.2.0: GMP 6.2.1, MPFR 4.1.0, and MPC 1.2.1.
- ISL/Graphite and gettext/NLS are disabled.
- Full GCC target execution tests additionally require DejaGNU and an AVR
  simulator; neither is part of this package.

## Build strategy

This is a stage-1 compiler: the C frontend, host driver programs, and target
AVR libgcc are built. No avr-libc headers, C runtime, or startup objects are
included, which breaks the dependency cycle cleanly.

The package runs on OHOS/AArch64 and emits AVR code. GCC's supported
`aarch64-unknown-linux-musl` host model is used because OHOS libc is
musl-derived. The target remains `avr`.

The stage-1 package selects GCC's `avr5` multilib family, which covers the
ATmega328P consumer test and keeps the full build within the repository CI
timeout. Other AVR multilib families remain outside this package scope.

The bootstrap pins both `double` and `long double` to the standard 32-bit AVR
ABI. Alternate 64-bit floating-point multilibs are not needed to build avr-libc
or validate ATmega328P code, and are outside this bootstrap package scope.

Fixed-point arithmetic is disabled for this bootstrap package. It is not used
by the avr-libc bootstrap flow or the ATmega328P consumer test, and its large
libgcc combination matrix exhausted the one-hour single-package runner window.

Official prerequisite archives are extracted directly into `gmp/`,
`mpfr/`, and `mpc/`; the upstream symlink-creating helper is not run.
All target binutils are resolved from the avr-binutils Conan package.

## Tests

- GCC contains 1,978 `gcc.c-torture/compile` sources.
- The GCC `selftest` target is invoked. The release configuration reports that
  internal self-tests are not enabled, so it is recorded as executed without an
  assertion count.
- Eight official no-header torture sources are compiled at `-O0` and
  `-O2` with the freshly built AVR compiler (16 compile checks).
- The package test compiles and links ATmega328P code with a volatile 16-bit
  division, validates that packaged `libgcc.a` is selected, and confirms
  AVR ELF architecture, `main`, and `__udivmodhi4` symbols.
- AVR code is not executed on the OHOS host.

## Single-package CI

```sh
CI_PACKAGES="archives/a/avr-gcc-bootstrap/14.2.0" zsh ci/conan/build_and_test.sh
```

Runner history:

- r13 confirmed `--with-libf7=no` removes libf7, but timed out in the
  fixed-point conversion matrix.
- r14 and r15 confirmed `fixed_point = no`; both exposed a reproducible HMDFS
  `getcwd` failure in the GCC selftest shell.
- r16 confirmed the logical `PWD`/shell `cd` fix and reached target-libgcc, but
  the default float ABI generated six multilibs and hit the 3600-second limit.
- r17 reduced the list to `.` and `avr5`, completed the package, and exposed
  the packaged GCC requirement for unprefixed `as`/`ld` dispatchers.
- r18 used the validated dispatcher root and passed the full shadow CI.

Successful runner:
`codex-avr-gcc-bootstrap-shadow-ci-r18-2245-20260819-181549-8619`

- Commit: `19bb09c0ce7c7c45a78d08c89f2e9e27b8d1d7d7`.
- Exit code: 0.
- Duration: 3155 seconds including 26 seconds waiting for the global lock.
- G0, L0, L1, L2, and L5 passed; L4 emitted a non-blocking patch scanner
  warning for the HMDFS shell patch.
- The final compiler reports only `.` and `avr5` multilibs, with
  `fixed_point = no` in the generated libgcc Makefile.
- Sixteen official torture sources compiled (eight at `-O0`, eight at `-O2`).
- The package test selected package-owned `avr5/libgcc.a`, linked a 102-byte
  `elf32-avr`/`avr:5` image, and verified `main` plus `__udivmodhi4`.
- L2 reports three plugin-wrapper commands as failed because this bootstrap
  intentionally uses `--disable-plugin`; the gate still passed the runnable
  compiler and gcov command set.