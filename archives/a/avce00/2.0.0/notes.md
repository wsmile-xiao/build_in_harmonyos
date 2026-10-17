# avce00 2.0.0 adaptation notes

## Source

- Upstream homepage: <http://avce00.maptools.org/>
- Source tarball: `http://avce00.maptools.org/dl/avce00-2.0.0.tar.gz`
- SHA256: `c0851f86b4cd414d6150a04820491024fb6248b52ca5c7bd1ca3d2a0f9946a40`
- Author: Daniel Morissette (dmorissette@mapgears.com)
- License: MIT

## Build system

- Pure GNUmakefile (no configure, no CMake, no meson).
- The Makefile hardcodes `CC = gcc`; the recipe overrides this via make variable `CC=...`.
- CFLAGS is also overridden to inject `-DCPL_LSB` (little-endian, default for OHOS aarch64)
  and `-DAVC_MAP_TYPE40_TO_DOUBLE` (upstream-recommended precision fix for type-40 fields).
- Builds a static library `avc.a` (renamed to `libavce00.a` in package) plus command-line
  tools: `avcimport`, `avcexport`, `avcdelete`.

## Dependencies

- None. The library is fully self-contained; it bundles its own CPL utility code
  (cpl_error, cpl_conv, cpl_string, cpl_dir, cpl_vsisimple, dbfopen).

## Public headers

- `avc.h` — main API header (E00 reader/writer, binary coverage reader/writer)
- `avc_mbyte.h` — multi-byte character support (Japanese DBCS)
- Bundled CPL headers: `cpl_error.h`, `cpl_port.h`, `cpl_conv.h`, `cpl_string.h`, `cpl_vsi.h`
- `dbfopen.h` — dBASE file reader (used internally by binary coverage support)

## Upstream tests

- The release tarball contains `avctest.c` which exercises binary coverage read/write,
  but it requires actual coverage data files that are not included in the tarball.
  There is no `make check` target in the GNUmakefile.
- The `ex_avcwrite` example program demonstrates write API but also requires
  a valid output directory.

## Test package

- Links against `libavce00` and exercises three API paths:
  1. Verifies `AVC_VERSION` macro matches `"2.0.0 ..."`
  2. Calls `AVCE00ReadOpen()` on a nonexistent path, expects NULL
  3. Calls `AVCE00WriteOpen()` on a nonexistent path, expects NULL

## Known limitations

- The source tarball URL uses HTTP (not HTTPS). The `avce00.maptools.org` server
  does not appear to support HTTPS. This is the official upstream download URL.
- The library dates from 2006 and uses some legacy C patterns (no `const` in some
  places, uses `GInt16`/`GInt32` typedefs via cpl_port.h).
- No shared library build is offered by the upstream Makefile; only static.

## OHOS-specific notes

- Byte order: OHOS aarch64 is little-endian, so `-DCPL_LSB` is correct.
- No `configure` script to worry about; the Makefile is invoked directly.
- The library has no POSIX-specific calls that would fail on OHOS (uses standard
  `stdio.h`, `stdlib.h`, `string.h`, `dirent.h` via the bundled CPL layer).
- `VirtualBuildEnv` cannot be used: its `printenv` call overflows the OHOS
  argument-list limit when the profile buildenv has many entries. The recipe
  writes a minimal `avce00_build_env` script instead.
- The Makefile uses `LFLAGS` (not `LDFLAGS`) for linker flags; the recipe passes
  `LFLAGS="$LDFLAGS"` to inject `--sysroot` and `-Wl,--code-sign`.
- `cpl_config.h` is an empty file but must be packaged (included by `cpl_port.h`).
- `AVCE00WriteOpen()` takes 3 arguments: `(path, cover_type, precision)`.
- OHOS requires `-Wl,--code-sign` for ELF binaries to execute.
- Compiled with 2 clang warnings (`-Wpointer-sign` in `avc_mbyte.c`); benign.

## Issue tracking

- Issue: 待补 (pending)
