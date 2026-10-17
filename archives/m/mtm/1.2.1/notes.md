# mtm 1.2.1 adaptation notes

- Upstream: `https://github.com/deadpixi/mtm`, tag `1.2.1` (no `v` prefix:
  `v1.2.1` returns GitHub's 404 page — an earlier `d5558cd4…` SHA was that
  ASCII error page, not the tarball).
- Source archive SHA256:
  `2ae05466ef44efa7ddb4bce58efc425617583d9196b72e80ec1090bd77df598c`
  (matches the pre-seeded `src/mtm-1.2.1.tar.gz`).
- License: GPL-3.0-or-later (upstream ships no LICENSE file; the notice is
  in mtm.c/README.rst "Copyright and License" section, GitHub reports
  GPL-3.0).
- Build system: single custom Makefile (28 lines), no configure, no test
  target (E097). Sources: mtm.c, vtparser.c, pair.c (unused by the build),
  config.def.h, mtm.1, mtm.ti, README.rst.
- Conan dependency: ncurses/6.6 (wide build; provides the `screen`
  terminfo entry via its runenv for the consumer test).
- The upstream `mtm` target runs `strip mtm` unconditionally; on OHOS the
  signing toolchain rejects stripped binaries (E077), so the recipe
  compiles `mtm.o vtparser.o` via make and links `mtm` itself — the same
  rule the Makefile uses, minus strip.
- The Makefile regenerates config.h with `cp -i config.def.h config.h`,
  which blocks interactively on rebuilds (E214 family); the recipe copies
  config.def.h to config.h itself (non-interactive) instead of invoking
  that rule — no patch needed.
- `-lutil` (forkpty) is dropped: OHOS musl merges libutil into libc and the
  sysroot ships only an empty stub `libutil.a` (`!<arch>` header, zero
  members). Verified by compiling/linking a forkpty probe against the OHOS
  sysroot with and without `-lutil` (both succeed; archive has no members).
- `-D_DEFAULT_SOURCE` is added to CFLAGS for ncursesw feature visibility
  on musl (E033 family).
- No patches: the default `config.def.h` builds unmodified (its A_ITALIC
  guard auto-detects ncurses version).
- Upstream tests: none. The tarball contains no test files, the Makefile
  has no test/check target, and README.rst only shows vttest screenshots
  annotated "but have not been tested" (line 44).
- Consumer test (1/1, registered in test_package/MANIFEST.yml): spawn `mtm`
  in a pty with TERM=screen, observe the hosted shell's output being
  multiplexed, delete the last node via command key Ctrl-g w (deletenode()
  on the root calls quit(EXIT_SUCCESS)), assert exit 0. The 4 internal
  assertions (binary exists, stays alive, output multiplexed, clean exit)
  count as ONE test case — not 4 tests. The test does not early-return on
  `can_run()`, so R34 correctly fails when the binary is missing.
- OHOS-specific test (1/1, registered in test_package/MANIFEST.yml):
  platform contract on the packaged binary — AArch64 ELF, musl interpreter,
  .codesign section present, no libutil in NEEDED, forkpty resolved by
  libc, real PTY run. Its 6 internal assertions (o1-o6) count as ONE test
  case — not 6 tests.
- The conan ncurses package installs headers flat (`include/curses.h`),
  while config.def.h includes `<ncursesw/curses.h>` on Linux; resolved
  without a patch via `-DNCURSESW_INCLUDE_H='<curses.h>'` (config.def.h's
  own escape hatch).
