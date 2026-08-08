# libsm

libSM is the X.Org implementation of the X Session Management protocol. It
provides client and manager APIs on top of libICE and installs the `libSM.so.6`
ABI used by X11 desktop applications.

## OHOS adaptation

- Builds the official libSM 1.2.6 release tarball with generated Autotools files.
- Recognizes the native `aarch64-linux-ohos` triplet in GNU config scripts.
- Disables optional libuuid support and uses xtrans for deterministic client IDs.
- Preserves the upstream `libSM.so.6` ABI and public X11 session headers.
- Uses package-relative pkg-config metadata and omits the obsolete `.la` file.
- Runs the mandatory upstream `make check` target and installed-package API tests.

## Dependencies

- `libice/1.1.2` supplies the ICE transport and public ICE API.
- `xorgproto/2025.1` supplies X11 protocol headers.
- `xtrans/1.6.0` supplies the network capability metadata used without libuuid.

## References

- https://gitlab.freedesktop.org/xorg/lib/libsm
- https://xorg.freedesktop.org/archive/individual/lib/
