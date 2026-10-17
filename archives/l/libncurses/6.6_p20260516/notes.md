# libncurses 6.6_p20260516 adaptation notes

## Baseline

- Official stable release: 6.6 (upstream release date 2025-12-30, patch date 20251230)
- Source SHA-256: `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`
- Build system: Autotools
- Conan reference: `libncurses/6.6_p20260516`
- Third-party Conan prerequisites: none
- Adaptation path: **path A (basic adaptation)** — no upstream source change beyond the
  portability patches listed below, no vendored dependency and no functional rework.

The version label follows the upstream version notation used by the adaptation task
(`6.6_p20260516`); the source archive is the upstream ncurses 6.6 stable release
(configure reports patch date `20251230`).

## Why a separate narrow package

The repository already ships the **wide-character** build of the same upstream release as
`archives/n/ncurses/6.6` (`--enable-widec`, `libncursesw.a`, `ncursesw6-config`). This
archive builds the **8-bit ABI** of that release into its own package.

The distinction is not cosmetic: since ABI 6 ncurses enables wide-character support *by
default* (`cf_dft_widec=yes` when `cf_cv_abi_version=6`), so "ncurses without
`--enable-widec`" is not a no-op — the narrow ABI has to be requested explicitly with
`--disable-widec`. The configuration changes the produced library names, the generated
config script and the pkg-config module set:

| Item | narrow (`libncurses`, this archive) | wide (`archives/n/ncurses/6.6`) |
|---|---|---|
| configure flag | `--disable-widec` | `--enable-widec` |
| ABI suffix | none | `w` |
| archives | `libncurses.a`, `libform.a`, `libmenu.a`, `libpanel.a`, `libncurses++.a` | `libncursesw.a`, `libformw.a`, … |
| config script | `bin/ncurses6-config` | `bin/ncursesw6-config` |
| pkg-config | `ncurses`, `form`, `menu`, `panel`, `ncurses++` | `ncursesw`, `formw`, `menuw`, `panelw`, `ncurses++w` |
| extended colors | not available (upstream restricts them to the wide library) | available |

## Package contract

- Build static libraries only. A shared ncurses library can shadow the platform
  `libncurses.so.6`/`libncursesw.so.6` that the system shell links, and the recipe
  rejects `shared=True`.
- Preserve all 86 entries declared by upstream `test/programs` and run the complete
  upstream `make -j1 check` target.
- Install the 18 public headers at the top-level include directory, the five static
  archives, the eleven terminal utilities and the complete terminfo database.
- Export the Conan CMake config (`libncurses::libncurses`), the upstream CMake
  `FindCurses` module contract, and relocatable `ncurses6-config` and pkg-config
  metadata. Every path in that metadata is derived from `${pcfiledir}` or from the
  config script location, so the package can be consumed from any prefix.

## Adaptation

The five patches are applied through Conan patch-ng in the exported source tree:

1. `0001-detect-compound-expr.patch` rejects the platform `expr` implementation when it
   cannot evaluate Autoconf compound expressions, so the GNU implementation present in
   the build environment is selected.
2. `0002-lib-mvcur-static-link.patch` permits the upstream `lib_mvcur` test to override its
   intentional stub symbols during a static link (`--allow-multiple-definition`).
3. `0003-install-headers-shell.patch` runs the generated header installer through the
   configured shell on HMDFS, where the generated script has no execute bit.
4. `0004-config-guess.patch` teaches the upstream platform detector to return
   `aarch64-unknown-linux-ohos` without `--build`, `--host` or `--target`.
5. `0005-link-test-ext-colors.patch` (new in this archive) fixes the non-wide
   configuration of the upstream link-completeness test. `ncurses/curses.priv.h` defines
   `USE_EXT_SP_FUNC_SUPPORT` as `(NCURSES_SP_FUNCS && NCURSES_EXT_FUNCS)`, but the
   extended **color** entry points (`init_extended_color`, `init_extended_pair`,
   `extended_color_content`, `extended_pair_content`, `extended_slk_color`, `find_pair`,
   `free_pair`, `alloc_pair`, `reset_color_pairs`) are implemented only when
   `NCURSES_EXT_COLORS` is on — and upstream restricts that define to wide-character
   builds. Without the patch the generated `link_test.c` references nine `_sp` symbols
   that the narrow library cannot provide, and `make check` fails at
   `ncurses/Makefile: link_test`. The patch retags exactly those nine declarations with a
   new `EXT_COLOR_SP_FUNC` tag and adds the matching, `NCURSES_EXT_COLORS`-aware guard, so
   the link-completeness test still covers every other implemented entry point instead of
   being switched off wholesale.

Build-time environment: configure runs through the available bash shell with a writable
`TMPDIR` under `/data/storage/el2/base`, `ac_cv_func_setfsuid=no` (unsupported syscall
151 in the target sandbox) and `--prefix=/` with `DESTDIR` staging. No patch or source
file uses an OHOS preprocessor conditional.

Each OHOS build step (`configure`, `make`, `make check`, `make install`) is executed with
its output bound to a log file under the private build root, and the log is echoed back
into the Conan output afterwards. This is required in practice: when `ConanFile.run()`
hands the recipe process output streams to the child, clang fails on the first
compilation unit without emitting a single diagnostic line and make only reports
`Error 1`, while the identical command succeeds from a shell *and* succeeds through the
same `run()` call as soon as its output is redirected to a file. Binding the output to a
log makes the step reproducible and keeps the full compiler output available for
diagnosis instead of losing it. `make -j1 make_hash` was the first compilation unit of the
build, which is why the failure looked like a single broken target.

## Validation

The upstream compilation and test targets run with `make -j1` (a single job keeps the
compiler-process peak at one and avoids the HMDFS jobserver). The test-package CMake
helper appends `-j1` after Conan's default job argument; GNU Make applies the final job
argument.

Upstream `make -j1 check` executes 144 entries and completes successfully:

- 86 `test/programs` entrypoints, all built (the upstream test programs are interactive
  and are not executed by upstream `make check`; upstream prints "The test-programs are
  interactive")
- 57 header self-containment compilations (every public and private header is compiled
  on its own)
- 1 `link_test` link-completeness check against `libncurses.a`

The `test_package` adds ten consumer workflows that compile, link against the packaged
static archives and run on the HarmonyOS target, with 39 consumer assertions:

1. `test_curses_module` — Conan CMake config target: version, `tputs` callback,
   packaged terminfo, window update and 8-bit `chtype` round trip (7 assertions)
2. `test_ncurses_components` — panel, menu and form lifecycles (3 assertions)
3. `test_ohos_platform` — HarmonyOS platform contract (4 assertions)
4. `test_find_curses_module` — upstream `FindCurses` module contract (7 assertions)
5. `ncurses6-config` consumer (3 assertions)
6. `form` pkg-config consumer (3 assertions)
7. `menu` pkg-config consumer (3 assertions)
8. `ncurses++` pkg-config consumer (3 assertions)
9. `ncurses` pkg-config consumer (3 assertions)
10. `panel` pkg-config consumer (3 assertions)

Four further assertions verify the package-level HarmonyOS static-linkage contract:
the package ships no shared object, all five static archives are present, the
config-script consumer binary is an AArch64 target binary, and that binary has no
`DT_NEEDED` entry for any curses or tinfo library.

Two platform details are handled by the consumer harness itself:

- The consumer build output is bound to a log file for the same reason as the recipe
  build steps (inherited output streams make the first compiler invocation fail
  silently); the log is echoed back into the Conan output.
- The `ncurses6-config` consumer selects its shell by probing candidates instead of
  trusting `PATH` alone: in the test phase `PATH` can resolve `bash` to a copy that the
  test-phase SELinux domain is not allowed to execute, which surfaces as
  `PermissionError` rather than a nonzero exit code.

Measured package contents (W3 `conan create`):

- 18 headers under `include/` (`curses.h` and `ncurses.h` at the top level)
- `libncurses.a`, `libform.a`, `libmenu.a`, `libpanel.a`, `libncurses++.a`
- 11 utilities under `bin/`, including `tic`, `infocmp`, `tput` and `ncurses6-config`
- 5 relocatable pkg-config modules and the relocatable `ncurses6-config`
- the complete terminfo database (`tic` reports 2897 entries; 2872 files land in the
  Conan package because case-variant terminfo names collapse on the target filesystem)
- 0 shared libraries

The `.ci-result.json` written by the embedded W3 step and its `reports/w3-local-ci.log`
are the authoritative record for one build of one commit. Both are gitignored by
repository convention and therefore do not travel with the PR; they can be reproduced
by re-running `ci/conan/setup.sh` and `ci/conan/build_and_test.sh
archives/l/libncurses/6.6_p20260516`. They are not duplicated here because they describe
a single run rather than the archived recipe.

## Known framework limitation (reported, not blocking)

`finish` step [3/10] runs the `clean-verify` helper, which re-applies every patch as a
plain `patch -p1 -i <file>` from the source root and ignores the Conan
`patches[].base_path` entry declared in `conandata.yml`. `0002-lib-mvcur-static-link.patch`
targets `ncurses/Makefile.in`, so that helper reports `Hunk 1 FAILED` even though Conan
patch-ng applies the same patch correctly (it honours `base_path`). The authoritative
build paths — `conan create` (recipe `source()` and `conan-verify` G2) and the platform CI
script `ci/conan/build_and_test.sh` (embedded W3) — apply all five patches without error,
which is what the W3 evidence above shows. SKILL.md marks step [3/10] as non-blocking for
exactly this class of helper limitation.
---

**编译结束**: 2026-09-19 00:52
**最终状态**: built
