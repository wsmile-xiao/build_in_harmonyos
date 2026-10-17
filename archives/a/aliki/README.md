# aliki

`aliki` measures Impulse Responses using a sine sweep and deconvolution
(written by Fons Adriaensen). The package builds two command-line tools:

- `aliki` — the X11 GUI for running measurements and analysing results.
- `aliki-rt` — the real-time capture program (ALSA or JACK).

## OpenHarmony adaptation

- Source: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/aliki-0.3.0.tar.bz2
- Build system: Makefile (no configure script)
- Dependencies (all published in the ohpcd registry): clxclient, clthreads,
  libsndfile, fftw3f, libxft, libx11, xorgproto, zita-alsa-pcmi, jack, alsa-lib
- The portability patch removes `-march=native`, the hardcoded
  `/usr/include/freetype2` and `/usr/X11R6` paths, parameterizes `INSTALL`
  for OHOS, uses `$(CXX)` from the Conan profile, and adds a `$(PCONFCFL)`
  slot for injecting dependency include paths.
- Neither tool can run to completion headless (GUI needs a display, capture
  needs audio hardware + shared memory), so the packaged smoke test verifies
  each binary loads its full runtime shared-library closure and reaches its
  normal early-exit path.
