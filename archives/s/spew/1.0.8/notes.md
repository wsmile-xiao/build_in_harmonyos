# spew 1.0.8 adaptation notes

## Build environment

- Build system: Autotools
- Compiler: clang/clang++ 15
- Target: OHOS armv8
- Runtime dependencies: popt/1.16, ncurses/6.6
- Build dependency: automake/1.18

## Upstream tests

The official tag has no test sources or registered Automake tests. The full upstream inventory is 0: `Makefile.am` only enters `src`, `man`, and `etc`; `src/Makefile.am` defines production libraries and the `spew` executable without `TESTS`, `check_PROGRAMS`, or `check_SCRIPTS`. The recipe still executes `make -j1 check` and treats failure as fatal.

## Adaptation

The Git tag omits generated Autotools files, so the recipe uses the published automake tool package and runs `autoreconf -fi`. The published ncurses package exposes the wide-character static ABI (`libncursesw`), so the configure library probe is adjusted before regeneration. The three upstream command modes are packaged as separate executable files to avoid HMDFS symlink replacement behavior.

## Added OHOS test

The consumer test uses a private writable directory supplied through `TMPDIR`, never `/tmp`. It runs the installed `spew`, `gorge`, and `regorge` binaries against a 4096-byte deterministic data file and checks the write, read, read-after-write integrity, and rejection of deliberately corrupted data. Together with version/help and executable checks, this provides ten real assertions.

## OHOS platform issues hit during adaptation

- E011: after `autoreconf -fi`, the generated `configure`/`config.status` ran `umask 077 && mktemp -d "./confXXXXXX"`. On HMDFS the resulting setgid directory is owned by the mapped uid and the generated `subs1.awk` could not be executed, so configure died with `could not setup config files machinery`. Fix: normalize `umask 077` to `umask 022` in the freshly generated scripts before `configure` runs.
- E007: the bundled 2021 `config.guess` has no HarmonyOS entry. Rather than passing a fake GNU triplet, a HarmonyOS branch for the real triplet `aarch64-unknown-linux-ohos` is inserted into `config.guess`, and the recipe then asserts that `config.sub` accepts that same triplet.
- The tag ships no `libgen.h` include although `basename()` is used; the `<libgen.h>` include is added before building.
---

**编译结束**: 2026-10-07 17:36
**最终状态**: built
