# netris 0.52 adaptation notes

## Baseline

- Version: 0.52 (1999 upstream release)
- Source: https://deb.debian.org/debian/pool/main/n/netris/netris_0.52.orig.tar.gz
- SHA256: 8bc770ebb2c3ead1611ca7a1a2f3d833e169536c78d53b3fcf49381164ee9706
- Build system: custom Configure script (not autoconf/automake)
- Upstream homepage: https://www.netris.org (original distribution site ftp.gwdg.de is defunct; Debian pool hosts the pristine upstream tarball)
- Dependencies: ncurses/6.6
- Status: built

## Build steps

netris does not use autotools. The build is a two-phase Configure + make workflow with post-Configure Makefile patching:

1. Run Configure with safe values (no paths containing '/'):
   ```bash
   bash Configure --cc "clang" --copt -O2 --cextra "-DNDEBUG"
   ```
   Configure uses `sed s/-VAR-/$VAR/g` which breaks when VAR contains '/' (e.g., include paths), so ncurses paths are not passed here. Configure detects `on_exit`, `sigprocmask`, `getopt.h`, `memory.h` and generates `Makefile`, `config.h`, `version.c`, `proto.h`.

2. Patch the generated Makefile to inject ncurses paths (via Conan `replace_in_file`):
   ```bash
   # CFLAGS: add ncurses include
   CFLAGS = $(CEXTRA) $(COPT) -I<ncurses_prefix>/include
   # LFLAGS: add library path and link flag
   LFLAGS = -L<ncurses_prefix>/lib -lncursesw
   ```
   The `-lncursesw` wide-character library is used (ncurses 6.6 provides `libncursesw`).

3. Build:
   ```bash
   make -j1
   ```
   Compiles 8 C sources (game.c, curses.c, shapes.c, board.c, util.c, inet.c, robot.c, version.c) and links two binaries: `netris` and `sr` (sample robot).

4. Package (no install target upstream):
   ```bash
   copy netris sr COPYING README -> package_folder/bin/
   ```

The recipe retrieves the compiler from `self.conf_info.get("tools.build:compiler_executables")` (clang) per R33, never using bare `${CC}`.

## Dependencies

- `ncurses/6.6` — runtime dependency for curses/terminfo. Fetched from ohpcd registry. Only this dependency; no other Conan requirements. Headers from `<ncurses_prefix>/include`, libraries from `<ncurses_prefix>/lib`.

## Makefile patch approach

Configure is not autoconf: it has no `--prefix` / `--with-ncurses` handling and its sed substitution is delimiter-unsafe. The recipe works around this by:
- Running Configure without ncurses paths to avoid sed failures (the `curses.h file not found` in `make depend` is expected and non-fatal; it only affects dependency generation before patching).
- After Configure, using `replace_in_file` to append `-I<ncurses_inc>` to `CFLAGS` and replace `LFLAGS =` with `LFLAGS = -L<ncurses_lib> -lncursesw`. This ensures the actual compilation uses the correct ncurses headers and links the wide-character library.

Upstream warnings during compilation (implicit `time`/`getopt`, `volatile void` return type, pointer-sign for `accept`) are pre-existing C89 style issues and do not affect the build.

## Upstream tests

- No `tests/` directory, no `make check` target, no ctest/pytest registration.
- `make check` returns "No rule to make target 'check'".
- Upstream README describes only manual interactive testing (run `./netris`).

## Verification results

- `conan create` (profile ohos-aarch64, Release, clang 15): PASS — G0-G4 + L2/L4/L5 all passed. Build produced ELF64 AArch64 OHOS binaries:
  - `netris` (links ncursesw) + `sr` (sample robot binary).
- `test_package` (R34 compliant): PASS — `self.run("netris -h")` executed the packaged binary via VirtualRunEnv, printed `Netris version 0.52` usage and exited 0. Negative test (bin/ removed) confirmed the test genuinely depends on the package.
- W3 local CI (`build_and_test.sh archives/n/netris/0.52`): PASS — L0 quality gates passed, dependencies resolved (ncurses/6.6), commands.json valid (type=tool), 1/1 package built successfully, ci-metadata.json generated.
- Binaries verified: `netris -h` outputs full usage (options -w/-c/-p/-k/-i/-r/-F/-s/-D/-S/-C/-H/-R) and exits 0.

---

**编译结束**: 2026-09-08
**最终状态**: built
