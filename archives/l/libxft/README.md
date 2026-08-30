# libXft

X.Org client-side FreeType font rendering library for X11 applications.

The OpenHarmony PC recipes keep the upstream `libXft.so.2` ABI, and their X11,
Xrender, Fontconfig, FreeType and protocol dependencies are explicit Conan
requirements. The two archived releases differ in build system upstream:

- `2.3.9` uses the official Meson build and needs no source patch.
- `2.3.8` is the last Autotools release. It carries `config.guess`/`config.sub`
  OHOS tuple patches, and its recipe builds a materialised, re-signed view of
  the dependency shared libraries so that autoconf's run probes — which link
  the whole dependency closure — can actually start on the device. See the
  version-level `notes.md` for the loader findings behind that design.
