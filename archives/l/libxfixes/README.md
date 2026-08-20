# libxfixes

libXfixes is the X.Org client library for the X Fixes extension. It provides
selection, cursor, region, pointer-barrier, and client-disconnect APIs on top
of Xlib.

## OHOS adaptation

- Builds the official 6.0.2 release with its generated Autotools files.
- Keeps upstream source behavior and the `libXfixes.so.3` ABI unchanged.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the upstream `make check` target, which has zero registered entries.
- Runs installed-package consumers that bind every public function symbol and
  validate the public protocol/version contract.

## Dependencies

- `libx11/1.8.13` supplies Xlib and the linked client runtime.
- `xorgproto/2025.1` supplies xproto, fixesproto, and xextproto headers.

libXext and libXrender are not direct dependencies of libXfixes.

## References

- https://gitlab.freedesktop.org/xorg/lib/libxfixes
- https://xorg.freedesktop.org/archive/individual/lib/
