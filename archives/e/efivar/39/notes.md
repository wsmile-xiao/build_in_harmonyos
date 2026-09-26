# efivar 39 adaptation notes

## Scope

- Conan reference: `efivar/39` (upstream tag `39` at rhboot/efivar; tag URL
  `https://github.com/rhboot/efivar/archive/refs/tags/39.tar.gz`)
- Target: HarmonyOS/OHOS armv8 using the SDK Clang 15 toolchain
- Build system: plain Makefile (no configure, no CMake) — same class as the
  archived liblinear recipe (explicit CC/AR/RANLIB make variables)
- Third-party Conan dependencies: none (the task sheet lists popt/1.16,
  which is an efibootmgr dependency, not required by efivar itself)
- Delivery: libefivar.so.1, libefiboot.so.1, libefisec.so.1, efivar and
  efisecdb CLI tools, headers under include/efivar/, COPYING

## Source

Official GitHub tag tarball
`https://github.com/rhboot/efivar/archive/refs/tags/39.tar.gz`, SHA256
`c9edd15f2eeeea63232f3e669a48e992c7be9aff57ee22672ac31f5eca1609a6`.
License LGPL-2.1-or-later (COPYING in the tarball).

## Problem 1: musl libc GNU extensions

The OHOS musl libc lacks `qsort_r()`, `secure_getenv()` and
`program_invocation_short_name` (all used by efivar sources). Patches
0003/0004 add `src/musl_shim.c` / `src/musl_shim.h`:

- `qsort_r` wraps `qsort` with `_Thread_local` context variables
  (thread-safe; no nested qsort_r inside efivar comparators)
- `secure_getenv` maps to `getenv` (HarmonyOS has no setuid/setgid)
- `program_invocation_short_name` initialised from musl `__progname` in a
  constructor

Patch 0002 adds `-include musl_shim.h` to CPPFLAGS; patch 0001 adds
`musl_shim.c` to LIBEFIVAR/LIBEFISEC sources and `musl_shim.o` as a
prerequisite of makeguids/efivar/efisecdb/thread-test.

## Problem 2: makeguids circular dependency

`make: Circular include/efivar/efivar-guids.h <- makeguids dependency
dropped.` — makeguids generates efivar-guids.h but makeguids.c includes
efivar.h which includes efivar-guids.h, so make drops the dependency and
makeguids never builds. The recipe manually compiles and links makeguids
(makeguids.o + util-makeguids.o + musl_shim.o) before running the full
make.

## Problem 3: cross-compilation CC/CCLD/HOSTCC/HOSTCCLD

All four make variables must point to the same SDK clang; `ERRORS=""`
disables `-Werror` (musl/clang produce new warnings), `WARNINGS="-Wall"`
keeps useful warnings. `ENABLE_DOCS=0` avoids asciidoc/xmllint.

## Upstream tests

`tests/Makefile` registers 14 integration tests in the TESTS variable:

| # | test | runs on OHOS | reason |
|---|------|--------------|--------|
| 1 | test.dmpstore.export | ✗ | needs grub2-editenv |
| 2 | test.efivar.export | ✗ | needs grub2-editenv |
| 3 | test.grubenv.var | ✗ | needs grub2-editenv |
| 4 | test.bootorder.var | ✓ | efivar CLI file round-trip vs goal |
| 5 | test.conin.var | ✓ | efivar CLI file round-trip vs goal |
| 6 | test.efivar.threading | ✓ | thread-test with local scratch dir emulating efivarfs (EFIVARFS_PATH env + probe getenv exemption) |
| 7 | test.parse.db | ✓ | efisecdb --dump annotate vs goal |
| 8 | test.esl.annotation | ✓ | efisecdb annotate vs goal |
| 9 | test.esl.sha256.unsorted | ✓ | efisecdb ESL creation vs goal |
| 10 | test.esl.sha256.ascending | ✓ | efisecdb ESL creation vs goal |
| 11 | test.esl.sha256.removal.descending | ✓ | efisecdb ESL removal vs goal |
| 12 | test.esl.sha256.addition.unsorted | ✓ | efisecdb ESL addition vs goal |
| 13 | test.esl.cert.addition | ✓ | efisecdb cert ESL vs goal |
| 14 | test.esl.cert.removal | ✓ | efisecdb cert removal vs goal |

The 3 grub2-editenv tests only need the tool to fabricate a 512-byte
input env file; OHOS has no grub. The 11 runnable tests are executed in
`build()` via `make -C tests <target>` when `can_run(self)`.

## Verification

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  exit 0 (2026-09-25, native OHOS worker)
- Upstream tests (run in build() via `make -C tests TOPDIR=... SHELL=bash`):
  **11/11 passed** — test.bootorder.var, test.conin.var,
  test.efivar.threading (1/2/4/64 threads all "thread test passed"),
  test.parse.db, test.esl.annotation, test.esl.sha256.unsorted,
  test.esl.sha256.ascending, test.esl.sha256.removal.descending,
  test.esl.sha256.addition.unsorted, test.esl.cert.addition,
  test.esl.cert.removal
- 3 skipped (environment): test.dmpstore.export / test.efivar.export /
  test.grubenv.var need grub2-editenv (OHOS has no grub; the tool only
  fabricates a 512-byte env input file)
- Gotcha: `make -C tests` needs TOPDIR passed explicitly (the top-level
  Makefile exports it but a bare sub-make does not) and SHELL=bash so the
  OHOS ELF binaries can exec (mksh cannot)
- Consumer test: `test_efivar` ran on target with bash -c + explicit
  LD_LIBRARY_PATH — "all 5 assertions passed"
  (efi_get_libefivar_version, efi_str_to_guid, efi_guid_is_empty,
  efi_guid_to_str round-trip (returns 36 on success), efi_guid_cmp)
- Installed CLI smoke: `efivar -L | grep grub` — OK
- Artefacts: lib/libefivar.so.1.39 + .so.1/.so, lib/libefiboot.so.1.39,
  lib/libefisec.so.1.39, bin/efivar, bin/efisecdb,
  include/efivar/*.h, lib/pkgconfig/*.pc, licenses/COPYING

## Consumer test

test_package/test_efivar.c links against libefivar via CMakeDeps and runs
on the target with bash -c + explicit LD_LIBRARY_PATH. 5 assertions:
efi_get_libefivar_version, efi_str_to_guid, efi_guid_is_empty,
efi_guid_to_str round-trip, efi_guid_cmp. Plus an installed-CLI smoke:
`efivar -L | grep grub` (exercises libefivar.so at runtime through the
packaged binary).
