# libnbd

NBD client library in userspace — client library for accessing Network Block
Device (NBD) servers, from the libguestfs project.

- Upstream: https://github.com/libguestfs/libnbd
- License: LGPL-2.1-or-later
- Version adapted: 1.9.6

## OHOS adaptation notes

- The git tag tarball ships no generated C sources: `lib/api.c`,
  `lib/states*.c`, `lib/states.h`, `lib/unlocked.h` and `include/nbd.h` are
  generated at build time by the OCaml generator (`generator/`). The recipe
  uses `tool_requires ocaml/4.14.1.1.4` and exports `OCAMLLIB` /
  `CAML_LD_LIBRARY_PATH` for the generator build.
- `configure` is bootstrapped with `autoreconf -i` (tarball has none).
- `lib/connect.c` vsock path is guarded by configure-detected header macros,
  because OHOS defines `AF_VSOCK` but ships no `linux/vm_sockets.h` /
  `sys/vsock.h` (see patches/0001-lib-connect.c.patch).
- All optional features disabled (gnutls/libxml2/fuse/python/golang/
  bash-completion) to keep the core library dependency-free on OHOS.

## Status

Version 1.9.6: built (2026-09-16). See `1.9.6/notes.md` and
`1.9.6/reports/` for details.