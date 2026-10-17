# libqrtr 1.4.0

The task package name is `libqrtr`; the upstream project is `libqrtr-glib`.

- Upstream tag: `1.4.0` (`69791f8f2a092d0ec8eb83cbe51dfc3d157c3079`)
- Build system: Meson
- Runtime dependency: `glib/2.88.0`
- Output: static `libqrtr-glib.a`; the published GLib dependency set includes a non-PIC static zlib, so a shared output cannot link it.
- Build configuration: GObject introspection and gtk-doc are disabled; the GLib Conan package omits the `gio-unix-2.0.pc` module, so the recipe generates a small pkg-config alias to its installed headers and existing `gio-2.0` component.
- Upstream tests: the source archive has no test directory or Meson test targets; `meson test` reports `No tests defined.`
- HarmonyOS consumer checks: URI generation, URI round trip, invalid URI rejection, and public GObject type registration (4/4).
- HarmonyOS adaptation: three narrow include-order patches address duplicate `sockaddr_storage` declarations from `sys/socket.h` and `linux/qrtr.h`.


### CI fix: Meson archiver resolution

CI #60874 downloaded the Debian source successfully, then Meson configure failed because Conan's generated machine file named the archiver `llvm-ar` without an absolute path; the worker PATH could not resolve it. `generate()` now pins `MesonToolchain.ar` to `tools.build:compiler_executables:ar` when configured, otherwise searches beside the configured C compiler and the OHOS SDK/HNP LLVM directories, then PATH. Missing tools fail early with a clear Conan configuration error. The source URL and SHA-256 are unchanged.
