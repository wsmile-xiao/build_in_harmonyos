# pygame

pygame is a Python framework for games and multimedia applications. It exposes
SDL2 video, audio, input, image, font, drawing, sprite, and timing facilities
through CPython extension modules and Python APIs.

## HarmonyOS PC adaptation

- Builds a `cp312-ohos_aarch64` wheel from the official 2.6.1 source archive.
- Consumes the published PIC-static `sdl2/2.30.10` package and derives private
  shared `libpygame_sdl2.so` and `libpygame_sdl2_mixer.so` runtimes, so SDL
  global state and SDL_mixer music registration are retained across modules.
- Enables SDL_image, SDL_mixer, SDL_ttf, FreeType, PNG, and JPEG support from
  Conan-managed dependencies.
- Omits PortMidi, X11 clipboard, and Linux V4L2 camera modules because those
  platform providers are not available in the published HarmonyOS dependency
  set.
- The published SDL_mixer package retains WAV and built-in minimp3; OGG and
  other optional decoders are reported as capability-scoped upstream skips.
- Applies one generated source patch so `Channel.stop()` clears its queued
  sound before SDL_mixer's finished callback can restart it.
- Signs native extension and bundled runtime ELF files before target execution.
- On HNP AppSpawn workers that reject `dlopen()` from the Conan user path
  (`E212`), the recipe records the exact failure and performs strict static
  ELF/signature/ABI checks; it does not count those sandbox checks as runtime
  tests. The complete runtime suite is reported from the standalone HarmonyOS
  PC validation run.

The current SDL2 dependency supports headless video/audio execution. Visible
HarmonyOS windows require the newer SDL2 NativeWindow backend and an in-process
ArkUI surface provider; that dependency migration is tracked as a known runtime
boundary for this version.

## Dependencies

- sdl2/2.30.10 (PIC static input; private SDL2/SDL_mixer runtimes derived in recipe)
- sdl2-image/2.8.12
- sdl2_mixer/2.8.1
- sdl2_ttf/2.24.0
- freetype/2.14.3.1
- libpng/1.6.58
- libjpeg-turbo/3.2.0
- libtiff/4.7.2
- libwebp/1.6.0
- zlib/1.3.1.1

The selected libtiff binary adds `xz/5.6.2` and `zstd/1.5.7` transitively.

## References

- https://www.pygame.org/
- https://github.com/pygame/pygame
- https://pypi.org/project/pygame/2.6.1/
