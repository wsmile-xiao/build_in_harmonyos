# layer-shell-qt 6.5.4 adaptation notes

## Source and dependencies

- Upstream release archive: KDE Plasma 6.5.4, SHA256 recorded in
  `conandata.yml` and verified from the downloaded archive.
- The implementation uses private QtWayland client APIs. It is built against
  the published `qtwayland/6.11.1` package and its `qtbase/6.11.1.2` base;
  Qt base alone does not provide the required private headers.
- ECM, Wayland and xkbcommon are declared as Conan dependencies. The recipe
  relocates dependency `.pc` files into its generated build folder so their
  original `prefix=/` values cannot point pkg-config at the device root.
- The `wayland/1.22.0` scanner dynamically loads libraries from the Conan
  cache, which HMDFS blocks. The recipe builds a static scanner from a
  separate checksum-pinned copy of the same upstream 1.22.0 source.
- The scanner's Expat build source uses the checksum-pinned upstream tag
  archive from GitHub codeload because the official release download timed out
  on the HarmonyOS device.

## Build scope

The static C++ interface library, Qt Wayland shell integration plugin and
upstream GUI smoke program are built from upstream CMake files. The separate QML plugin is optional in the
upstream project; this recipe disables it because the available QML package
graph pins a different `qtbase` reference from the QtWayland private-API
package. The C++ API and Wayland plugin remain enabled. The small CMake patches
make this option explicit and remove the unused QML link from the upstream
smoke test.

The upstream GUI smoke program is executed with Qt's offscreen platform, so it
checks application/API startup without requiring a compositor. The fresh
consumer test separately checks the exported C++ API defaults and setters.
No Wayland compositor protocol exchange is claimed by these checks.

QtWayland 6.11.1's generated private core protocol header and Wayland 1.22's
client protocol header use the same generic include guard. The recipe applies
a small source include-order patch so QtWayland's `wl_fixes` declarations are
visible before the older Wayland header is included.

The consumer run also needs the library's Conan dependency paths to reach
QtWayland's transitive Wayland dependencies. The shared targets use `DT_RPATH`
so the OHOS dynamic loader can resolve those dependencies from the Conan cache.
