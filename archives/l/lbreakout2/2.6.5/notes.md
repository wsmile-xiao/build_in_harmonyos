# LBreakout2 2.6.5 OHOS adaptation notes

## Upstream facts

- Official project page: https://lgames.sourceforge.io/LBreakout2/ (upstream is
  no longer maintained; 2.6.5 is the final release, official recommendation is
  LBreakoutHD).
- Source archive: `lbreakout2-2.6.5.tar.gz` from the SourceForge project
  `lgames/lbreakout2/2.6`, SHA-256
  `9104d6175553da3442dc6a5fc407a669e2f5aff3eedc5d30409eb003b7a78d6f`.
- License: GPL-2.0-or-later (COPYING is the plain GPLv2 text; the source file
  headers grant "version 2 ... or (at your option) any later version").

## Build configuration

- Old-style autotools (configure.in + Makefile.am, autoconf 2.59 era). Built
  in-tree (`self.folders.build = "."`) because the top-level
  `lbreakout2.desktop` rule reads `lbreakout2.desktop.in` through a shell
  redirection, which ignores the VPATH search of out-of-tree builds.
- SDL 1.2 comes from `sdl12-compat/1.2.68` (the original SDL 1.2 tree does
  not build on OHOS); audio through `sdl-mixer/1.2.12`; PNG data through
  `libpng/1.6.58` on `zlib/1.3.1.1` (libpng provides the `libpng.so` alias
  that the hard `AC_CHECK_LIB(png)` probe needs).
- SDL discovery: the vendored 1999-era `AM_PATH_SDL` macro (acinclude.m4)
  requires a `sdl-config` script and overwrites `SDL_CFLAGS`/`SDL_LIBS` from
  its output, so exporting those variables does not help. The sdl-config
  shipped inside the sdl12-compat package has the package builder's absolute
  prefix baked in. The recipe therefore writes a small sdl-config shim into
  the build folder that reports the resolved dependency
  (`-I<pkg>/include/SDL`, `-L<pkg>/lib -Wl,-rpath-link,<pkg>/lib -lSDL-1.2`)
  and passes it through `SDL_CONFIG=`, which `AC_PATH_PROG` keeps when the
  variable is already set. Same approach as the SDL_CFLAGS/SDL_LIBS override
  used by the sdl-mixer/sdl-image recipes, adapted to the older macro.
- `--disable-sdltest` plus explicit `--build=x86_64-unknown-linux-gnu` and
  `--host=aarch64-unknown-linux-ohos` pin the 2004-era configure into cross
  mode: the bundled version-check program is never executed and neither
  config.guess nor conftest execution gets in the way (knowledge E064).
- `--disable-nls`: the tarball bundles a 2004-era `intl/` tree that is not
  cross-buildable with the OHOS toolchain; the game falls back to English.
- `--disable-network`: SDL_net 1.2 is not available in the archive set
  (only sdl2_net), so the client's NETWORK_ENABLED paths are dropped. The
  standalone `lbreakout2server` socket daemon is still built and installed
  because upstream ships it unconditionally in SUBDIRS.
- Audio stays enabled (default): only WAV chunks are played through
  SDL_mixer, and a failing `Mix_OpenAudio` at runtime is non-fatal
  (gui/stk.c continues with sound disabled).
- Install layout: the prefix is the Conan package folder itself and
  `make install` runs with an explicit empty `DESTDIR=`. LBreakout2 compiles
  `SRC_DIR` (game data, `$datadir/lbreakout2`) and `HI_DIR` (highscore
  chart, `$localstatedir`) into the binary, so the relocation-friendly
  `--prefix=/` + DESTDIR scheme would leave the game looking for its data
  under a nonexistent `/share/lbreakout2` (verified: SIGSEGV during
  startup with the default scheme). With the package folder as prefix the
  installed binary finds `share/lbreakout2` and writes highscores to
  `<pkg>/var`; when that directory is not writable the game falls back to
  `~/.lgames` (client/chart.c).

## Patches

1. `0001-config.sub.patch` - teach the vendored 2004 config.sub about
   `aarch64` and `linux-ohos` (same style as sdl-image; config.guess stays
   pristine because both triplets are passed explicitly).
2. `0002-configure-umask.patch` - config.status scratch directory umask
   077 -> 022; HMDFS rejects the 0700 directories created by the old
   mktemp/mkdir fallback (knowledge E011, same fix as sdl-mixer).
3. `0003-client-main-config-h.patch` - include config.h in client/main.c so
   `AC_USE_SYSTEM_EXTENSIONS`' `_GNU_SOURCE` makes the `setresgid` prototype
   visible (musl declares it under _GNU_SOURCE); without it clang 15 warns
   about the implicit declaration of the privilege-drop call.

## Tests

- Upstream 2.6.5 has no test suite: no `TESTS`/`check_PROGRAMS`/`check:`
  target in any Makefile.am, no test directory or test sources in the
  tarball, and no test instructions in README/README-SDL.txt/TODO.
- test_package therefore exercises the real installed product:
  - `test_commands.py` checks both installed commands and the game data,
    then runs `lbreakout2` headless (SDL dummy video/audio drivers) and
    requires it to survive its startup window: the banner, SDL_Init
    (video, audio, timer, joystick), the 640x480x16 software display, PNG
    and theme loading, the highscore chart, and the menu loop all have to
    succeed for the process to still be alive at the timeout. The game has
    no `--version`/`--help` mode, so "still running" is the pass
    criterion; any early exit (missing library, STK_ABORT, missing data)
    fails the test.
  - `test_sdl_runtime.c` links against the same SDL/SDL_mixer dependencies
    and drives the exact API surface the game uses at startup.
- Manual post-install verification (device, SDL dummy drivers): the game
  prints its banner, loads theme 'AbsoluteB', saves the highscore chart in
  the package var directory, and keeps running until killed by timeout.

## Findings

- SDL_INIT_JOYSTICK succeeds on the OHOS SDL2 runtime (dummy drivers);
  no joystick-specific guard is needed in the game code.
- `lbreakout2 --version`/`--help` do not exist (argv is only interpreted
  as levelset files), so the CI L2 smoke reports a non-blocking warning;
  the headless run in test_package is the real smoke verification.
- musl compatibility: no glibc-only calls found; `setresgid` exists on
  musl (declaration fixed through patch 0003).
