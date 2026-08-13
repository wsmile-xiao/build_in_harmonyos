# libxcb

X11 C Binding (XCB) — replaces Xlib for low-level X Window System protocol access.

## Upstream

- Homepage: https://gitlab.freedesktop.org/xorg/lib/libxcb
- Releases: https://xorg.freedesktop.org/archive/individual/lib/

## Dependencies

| Dependency | Purpose |
|-----------|---------|
| xcb-proto | XML protocol descriptions + xcbgen Python generator (build-time) |
| xorgproto | X11 protocol headers (X11/X.h, Xfuncproto.h, etc.) |
| libxau | X authority library (runtime) |
| libxdmcp | X Display Manager Control Protocol (optional runtime, for XDM auth) |
| check | unit testing framework (build-time, enables upstream HAVE_CHECK test suite) |

## Build

Autotools (`configure` + `make`). The X.Org release tarball ships pre-generated
configure + Makefile.in, so no autoreconf is needed.

## OHOS adaptation

Patches (in `patches/`):
- E205: config.guess/config.sub HarmonyOS triplet
- E002: configure umask 077 -> 022 for HMDFS temp-dir exec
- shebang: /bin/sh -> /data/service/hnp/bin/bash

The recipe supplies `--build=aarch64-unknown-linux-gnu --host=...` because OHOS
file systems are noexec and configure conftest programs cannot execute on target.
