# libxrender

libXrender is the X.Org client library for the X Render extension. It exposes
format discovery, picture composition, glyph, geometry, cursor, filter, and
gradient operations through Xlib.

## OHOS adaptation

- Builds the official 0.9.12 release with its generated Autotools files.
- Keeps upstream source behavior and the `libXrender.so.1` ABI unchanged.
- Applies narrow `config.sub` and `config.guess` portability patches, then
  derives a fail-closed build-local `configure` copy for writable HMDFS
  temporary directories.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the upstream `make check` target, which has zero registered entries;
  the exact W3 r11 run recorded `0/0` upstream tests and `2/2` consumers.
- Links every public function and executes the display-independent color API
  on the authorized OHOS/arm64 target.

## Dependencies

- `libx11/1.8.13` supplies Xlib and the linked client runtime.
- `xorgproto/2025.1` supplies xproto and renderproto headers.

libXext is not a direct dependency. The lower X11 closure remains transitive
through libX11.

## References

- https://gitlab.freedesktop.org/xorg/lib/libxrender
- https://xorg.freedesktop.org/archive/individual/lib/
