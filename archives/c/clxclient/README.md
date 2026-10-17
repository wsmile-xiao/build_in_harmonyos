# clxclient

`clxclient` is a small C++ wrapper library around the X11 protocol (Xlib +
Xft + FreeType), written by Fons Adriaensen. It provides display, window,
button, scroll, menu and meter widget classes used by his audio tools.

## OpenHarmony adaptation

- Source: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/clxclient-3.9.2.tar.bz2
- Build system: Makefile (no configure script)
- Runtime dependency: Xft, X11, FreeType and clthreads provided by Conan packages
- The portability patch removes `-march=native` and the `pkgconf` FreeType
  probe, parameterizes `INSTALL` for OHOS, drops `ldconfig`, and installs the
  full `libclxclient.so` symlink chain.
- The library is exercised by a packaged consumer test that drives the
  `X_resman` resource database without needing an X display.
