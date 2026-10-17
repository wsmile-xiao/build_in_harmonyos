# libxext

libXext is the X.Org client library for miscellaneous X11 extensions,
including SHAPE, MIT-SHM, SYNC, DBE, DPMS, and XTEST-related interfaces.

## OHOS adaptation

- Builds the official release with its generated Autotools files.
- Keeps upstream source behavior and the `libXext.so.6` ABI unchanged.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the upstream `make check` target, which has zero registered entries.
- Runs installed-package consumers for display-independent XSync operations
  and the extension registry/error-handler lifecycle.

## Dependencies

- `libx11/1.8.13` supplies Xlib and the linked client runtime.
- `xorgproto/2025.1` supplies xproto and xextproto headers.

libxcb and xtrans remain transitive dependencies of libX11.

## References

- https://gitlab.freedesktop.org/xorg/lib/libxext
- https://xorg.freedesktop.org/archive/individual/lib/
