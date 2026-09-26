# jkmeter

`jkmeter` is a JACK audio meter by Fons Adriaensen: a K-System loudness
meter (K12/K14/K20, horizontal or vertical) with an optional stereo
correlation meter, rendered as an X11 GUI.

## OpenHarmony adaptation

- Source: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jkmeter-0.9.0.tar.bz2
- Build system: bare Makefile (source/Makefile, no configure script)
- Dependencies (all published in the ohpcd registry): clxclient/3.9.2,
  clthreads/2.4.0, jack/1.9.22, libpng/1.6.58.3, libsndfile/1.2.2 (headers
  only), freetype/2.14.3, libx11/1.8.13, libxft/2.3.8, xorgproto/2025.1
- The portability patch drops `-march=native`, replaces the
  `pkg-config --cflags freetype2` probe with the `$(PCONFCFL)` injection
  slot, and parameterizes the bare-Makefile install rules as `$(INSTALL)`
  with an OHOS-safe default (`/bin/install`).
- The package installs `bin/jkmeter` plus the 24 meter/scale PNG assets
  under `share/jkmeter/` (loaded at runtime from the compiled-in
  `/usr/local/share/jkmeter` default).
- jkmeter cannot run to completion headless (X11 display + JACK server are
  required); the packaged smoke test therefore asserts the loading layer
  (full shared-library closure + ELF self-signature) and the process layer
  (`-help` version banner; clean exit 1 with "Can't open display." when no
  X server is present) instead of claiming a full GUI run.
