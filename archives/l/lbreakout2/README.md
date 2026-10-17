# LBreakout2

LBreakout2 is the LGames breakout/arkanoid style arcade game for SDL 1.2
(upstream 2.6.5 is the final release; the project is no longer maintained).

## OHOS adaptation

- Builds the `lbreakout2` client and the `lbreakout2server` daemon with the
  upstream 2004-era autotools build, patched for aarch64-linux-ohos.
- Uses the published SDL 1.2 compatibility layer, SDL_mixer, libpng and zlib
  Conan dependencies; networking is disabled (no SDL_net 1.2 in the archive
  set) and NLS is disabled (bundled 2004 gettext).
- The game data is installed to `<package>/share/lbreakout2` and the binary
  resolves it through the compile-time SRC_DIR; highscores default to
  `<package>/var` with a `~/.lgames` fallback.
- Runs headless on OHOS through the SDL dummy video/audio drivers; audio is
  WAV-only via SDL_mixer and degrades gracefully when no audio device is
  present.

## Upstream

- Project page: https://lgames.sourceforge.io/LBreakout2/
- Source archive: SourceForge `lgames/lbreakout2/2.6/lbreakout2-2.6.5.tar.gz`
- License: GPL-2.0-or-later
