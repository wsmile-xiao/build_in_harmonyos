# Nestopia

Nestopia is a portable, cycle-accurate NES/Famicom emulator written in C++.

## Features

- Cycle-accurate NES/Famicom emulation core (`Nes::Core::Api::*`)
- Header-only NTSC video filter (`source/nes_ntsc`)
- FLTK front-end with SDL2 input support
- Supports iNES, UNIF, FDS, NSF and XML image formats
- zlib/libarchive based archive handling

## HarmonyOS PC adaptation (1.53.2)

- Autotools build with `autoreconf` bootstrap; the upstream tarball does
  not ship a generated `configure`.
- All dependency flags (`ZLIB/LIBARCHIVE/SAMPLERATE/SDL2/LIBEPOXY/FLTK`)
  are supplied as absolute Conan package paths. Host `pkg-config` and
  `fltk-config` probing is disabled so no host-native flags can leak into
  the OHOS build (patches/0001).
- OHOS exposes EGL/GLES2 but not GLX/desktop OpenGL, so the in-repo
  `libfltk/1.3.11` package has no `libfltk_gl.a`. The FLTK front-end's
  `Fl_Gl_Window` symbol set is provided by `fltkui/fltk_gl_ohos.cpp` with
  an honest `can_do()==0` capability probe (patches/0002+0003). The GUI
  display path cannot run headless on OHOS and is verified at link level
  only.
- The emulation core is additionally archived into `libnestopia_core.a`
  and shipped with its headers, enabling headless consumer tests that
  drive the core APIs without any FLTK/SDL/GL initialisation.
- The core-API smoke test loads a programmatically generated minimal iNES
  ROM (16-byte header + 16 KiB PRG + 8 KiB CHR), executes N frames and
  asserts the frame counters and the reset state.

## Dependencies

- zlib/1.3.1.1, libarchive/3.8.7, libsamplerate/0.2.2, sdl2/2.32.10,
  libepoxy/1.5.10, libfltk/1.3.11 (via Conan)
- Build tools: autoconf/2.72, automake/1.18, autoconf-archive/2024.10.16

## References

- Upstream repository: https://github.com/0ldsk00l/nestopia
- Upstream tag: `1.53.2`
- License: GPL-2.0-or-later