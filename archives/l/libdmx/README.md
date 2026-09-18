# libdmx

libdmx is the X.Org client library for the Distributed Multihead X
(DMX) extension: querying and reconfiguring the screen, window,
desktop, and input topology of a DMX (Xdmx) proxy X server.

## OHOS adaptation

- Builds the official libdmx 1.1.5 release with its generated
  Autotools files; no source patches.
- Keeps upstream behavior and the `libdmx.so.1` ABI unchanged.
- Uses package-relative pkg-config metadata and omits the obsolete
  `.la` file.
- Runs the upstream `make check` target, which has zero registered
  entries.
- Runs installed-package consumers for full symbol relocation,
  protocol/ABI contract validation, and a HarmonyOS ELF gate
  (ELF64 AArch64, NEEDED closure, RPATH/RUNPATH hygiene).

## Dependencies

- `libx11/6.4.0` supplies Xlib and the linked client runtime.
- `libxext/6.4.0.1` supplies the Xext/extutil extension bookkeeping
  used by every DMX entry point.
- `xorgproto/2025.1` supplies dmxproto/dmx/xextproto headers.

libxcb, libxau, libxdmcp, and xtrans remain transitive dependencies of
libX11.

## References

- https://gitlab.freedesktop.org/xorg/lib/libdmx
- https://xorg.freedesktop.org/archive/individual/lib/
