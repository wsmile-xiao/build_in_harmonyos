# libice

libice is the X.Org implementation of the Inter-Client Exchange protocol. It
provides connection setup, message transport, authentication-file utilities,
and the `libICE.so.6` ABI used by X11 session-management libraries.

## OHOS adaptation

- Builds the official release tarball with its generated Autotools files.
- Recognizes the native `aarch64-linux-ohos` triplet in GNU config scripts.
- Keeps upstream source behavior and ABI versioning unchanged.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the upstream `make check` target and real installed-package API tests.

## Dependencies

- `xorgproto/2025.1` supplies public X11 protocol headers.
- `xtrans/1.6.0` supplies the transport implementation sources and metadata
  consumed while building libICE.

## References

- https://gitlab.freedesktop.org/xorg/lib/libice
- https://xorg.freedesktop.org/archive/individual/lib/
