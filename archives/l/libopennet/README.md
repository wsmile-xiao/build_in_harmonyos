# libopennet

libopennet is a small C library by Roy Keene that provides a stdio-like
API (`fopen_net`, `fread_net`, `fgets_net`, `fseek_net`, `open_net`,
`read_net`, ...) which transparently opens both local files and
`http://` URLs, so programs read remote resources exactly like local
files. It is pure libc + POSIX/BSD sockets with zero external
dependencies.

License: LGPL-2.1-or-later (opennet.c/opennet.h); net.c is
GPL-2.0-or-later.

## OHOS adaptation

- Builds the official 0.9.9 release tarball with its bundled 2004-era
  autoconf configure + handwritten Makefile.in (in-source build; the
  `%_shr.o` pattern rule has no VPATH support).
- Upstream always builds both `libopennet.a` and `libopennet.so`; the
  `shared` option (default `False`, system-name library) only selects
  what the consumer links against and what gets packaged — the shared
  package mirrors the upstream install layout (`libopennet.so.0.9.9`
  real file + `so.0`/`so` symlinks) with a proper
  `-Wl,-soname,libopennet.so.0`.
- Two source patches are required: an upstream bug fix
  (`fseek_net()` self-recursion and the uninitialized `off_t length`
  in `fopen_net()`) and an HMDFS configure fix (drop `umask 077` from
  the confstat mktemp/mkdir lines; E114).
- Knowledge-graph reuse only (no new entries): E007 (explicit
  `--build`/`--host` triplets for the OHOS-unaware config.guess),
  E114 (configure umask/mktemp), E232 (`/system/bin/sh` configure
  prefix on the native OHOS executor), E074 (`make -j1`), E274
  (soname injection), E461 (AF_UNIX abstract namespace for the socket
  test), E298 (`self.run(..., env="conanrun")`).
- Upstream has no formal test suite (`make test` builds a no-assertion
  demo); it is run offline as a smoke test only.

## Consumer tests

The test package builds one consumer binary and runs it in both static
and shared modes (4 tests, not double-counted):

1. local-file stdio API (covers both patch-0001 regressions),
2. fd API including the real upstream `lseek_net` stub behavior,
3. OHOS-specific AF_UNIX abstract-namespace socket read (E461),
4. offline network API against a forked loopback HTTP server
   (127.0.0.1 only; PASS never depends on public internet access).

`test()` additionally runs the OHOS ELF checks: ELF64 + AArch64,
NEEDED `libopennet.so.0` for shared consumers (absent for static), and
RPATH/RUNPATH inspection, all via readelf.

## Dependencies

None — pure libc and POSIX/BSD socket APIs. Settings are restricted to
Linux/OHOS.

## References

- https://www.rkeene.org/oss/libopennet/
- https://www.rkeene.org/files/oss/libopennet/libopennet-0.9.9.tar.gz
