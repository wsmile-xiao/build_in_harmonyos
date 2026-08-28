# libXft

X.Org client-side FreeType font rendering library for X11 applications.

The OpenHarmony PC recipe keeps the upstream `libXft.so.2` ABI and uses the
official Meson build. Its X11, Xrender, Fontconfig, FreeType, and protocol
dependencies are explicit Conan requirements.
