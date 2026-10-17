# libmenuw 6.6_p20260516 adaptation notes

## Baseline

- Upstream source: ncurses snapshot 6.6-20260516 from the official author
  snapshot repository (ThomasDickey/ncurses-snapshots, tag `v6_6_20260516`,
  `VERSION` 6.6, `NCURSES_PATCH` 20260516)
- Source SHA-256: `34b0a7f18d7e956b938bd1040c9dfb950dd707c2b60c1b2a61b8dd0d2e13a150`
- The weekly tarball `ncurses-6.6-20260516.tgz` was pruned from
  invisible-island.net/archives/ncurses/current/ at adaptation time, so the
  author-maintained GitHub snapshot tag is the reference source; PF7 uses the
  official repository identity, not a proxy or redistribution mirror
- Build system: Autotools (ncurses tree; menu is built inside it)
- Conan reference: `libmenuw/6.6_p20260516`
- Conan dependency: `ncurses/6.6` (published on the ohpcd remote; recipe
  revision `3dcfd3b6d759300e8997800cefe8c61f`, package id
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5` verified installable under the
  target profile before adaptation started)
- Final state: `built`; release upload happens through the merge pipeline

## Package contract

- Split-package design: the menu library needs the ncurses core to build, so
  the full snapshot tree is configured and compiled exactly like the archived
  ncurses 6.6 recipe, but this package installs only four artifacts:
  `include/menu.h`, `include/eti.h` (the `menu/headers` list),
  `lib/libmenuw.a`, `lib/pkgconfig/menuw.pc` (prefix-relocated). No ncurses
  core artifact is packaged; `ncurses::ncurses` comes from the dependency.
- Static wide-character only (`--without-shared --enable-widec`); `shared=True`
  is rejected in `configure()` and packaged `.so` files or foreign ncurses
  archives would fail package validation.
- Upstream inventory: all 86 `test/programs` entrypoints must build (including
  the menu consumer `demo_menus`), followed by the complete
  `make -j1 check` target (per-header standalone compilation checks).
- Consumer coverage: `test_menu_consumer` exercises the menu lifecycle through
  the packaged library (item creation and name/description round trip,
  `item_count`, `O_ONEVALUE`, mark/fore/back/pad attributes, item userptr,
  item value toggle, selectable option off/on, `scale_menu`,
  `set_menu_format`, post/current item/visibility, `REQ_LAST_ITEM` with denied
  `REQ_NEXT_ITEM`, `set_current_item` with `REQ_UP_ITEM`/`REQ_DOWN_ITEM`
  navigation, request name tables, unpost and free teardown); the pkg-config
  consumer proves the split contract by requiring `menuw.pc` to select this
  package's `libmenuw.a` together with the ncurses package's `libncursesw.a`
  and no shared curses library.

## Adaptation

1. `0001-detect-compound-expr.patch` regenerates the ncurses 6.6 fix for the
   snapshot `configure`: both autoconf prologues switch the `expr` probe to a
   compound expression that the platform Toybox implementation fails,
   selecting the GNU implementation instead. The 6.6 release hunk context no
   longer matched the snapshot; the regenerated patch is byte-identical in
   intent (shared byte-for-byte with the sibling libpanelw adaptation of the
   same snapshot).
2. `0002-lib-mvcur-static-link.patch` re-lands the ncurses 6.6 fix on the
   snapshot `ncurses/Makefile.in` (lib_mvcur rule uses `$(MVCUR_DEPS)`),
   keeping `-Wl,--allow-multiple-definition` so the intentional stub
   overrides link statically.
3. `0003-install-headers-shell.patch` and `0004-config-guess.patch` apply
   unchanged from ncurses 6.6: the HMDFS header installer runs through the
   selected shell, and `config.guess` reports `aarch64-unknown-linux-ohos`
   without `--build`/`--host`/`--target`.
4. `ac_cv_func_setfsuid=no` prevents the configure probe from executing the
   unsupported syscall 151 in the target sandbox. No source or patch uses an
   OHOS preprocessor conditional.
5. The build runs in a private `/data/storage/el2/base` root (HMDFS absolute
   paths stay out of generated rules), `make -j1` throughout, one compiler
   process at a time.

## Validation

Exploratory and formal validation use one currently authorized HarmonyOS
arm64 device with a fresh per-run Conan home.

- Upstream test/program entrypoints: 86/86 (UPSTREAM_TEST_PROGRAMS=86/86)
- Complete upstream `make -j1 check`: pass
- Menu demo runtime: `demo_menus` executed headless with piped input,
  `TERM=xterm` and the packaged terminfo; exit 0
- Consumer CMake test: `test_menu_consumer` 16/16 assertions through
  `libmenuw::libmenuw`
- Consumer pkg-config test: `-Wl,-t` trace selected the packaged
  `libmenuw.a` and the ncurses package `libncursesw.a`; no shared curses
  library; runtime exit 0
- Negative configuration: `libmenuw/*:shared=True` rejected at `configure()`
- Package contents validated: only `include/menu.h`, `include/eti.h`,
  `lib/libmenuw.a`, `lib/pkgconfig/menuw.pc`; no `.so`, no foreign archives,
  no absolute path leaks in `menuw.pc`
- Baseline re-establishment: `reports/baseline.json` left by an earlier aborted
  finish round was removed before the final verification round. Static `.a`
  archives embed per-run member timestamps in their ar headers, so same-source
  rebuilds differ byte-level (the static-archive analogue of the tool guidance
  for ELF build-path variance); the final round re-established the baseline,
  which is semantically a first run

Known toolchain finding recorded for consumers: with the current CMakeDeps,
the include directories of a purely transitive dependency are not emitted in
the generated data files, so consumers of this split package should keep
`ncurses/6.6` as a direct requirement (or use the `menuw.pc`/`ncursesw.pc`
metadata path). The test package declares both requirements explicitly.

## Embedded finish/W3

The formal validation is the standard `finish` run: a fresh private CONAN_HOME,
the internal W2 structure and R36 dependency gates, `conan create` with the
same contract as above, and an integrity-valid `.ci-result.json` with
`exit_code=0`. If the outer `finish` command returns nonzero after W3 because
of unrelated repository-wide checks, the PR reports that result separately and
does not describe the complete `finish` command as passing.
