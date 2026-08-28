# libcext 1.3.2 adaptation notes

- Upstream source is the ESO ftp release `cext-1.3.2.tar.gz`. The archive is
  byte-verified by the SHA256 in `conandata.yml` and the upstream `.md5` file
  (`c38e62a01f1ba77ceeb9af51bef227f8`).
- libcext is ESO's C utility library, used to implement the Common Pipeline
  Library (CPL). Upstream homepage: https://www.eso.org/sci/software/cpl/
- License: LGPL-2.1-or-later (stated in COPYING and in README "License").
- The project uses Autotools. The release archive ships a pre-generated
  `configure` and `Makefile.in`, so `autoreconf` is **not** needed and is not
  run. `admin/config.sub` (2022-01-03) already accepts `aarch64`, so no
  config.sub patch is required (zero source patch).
- `configure.ac` calls `LT_INIT([disable-static])`, so the upstream default is
  shared-only; this recipe defaults to `shared=True` to match.
- The library is `libcext` with libtool `-version-info 3:0:3`, producing
  `libcext.so.3.0.3` / SONAME `libcext.so.3`.
- No Conan dependencies. libcext is self-contained (only libc functions).

## OHOS environment handling (zero source patch)

- `configure` contains `umask 077` for the config.status temp dir. On setgid
  HMDFS this yields an unwritable `drwx--S---` dir (E114). Replaced with
  `umask 022` in the generated `configure` at build time — not a source patch.
- `configure` has a `#! /bin/sh` shebang; on OHOS `/bin/sh` may be absent. The
  shebang and `CONFIG_SHELL`/`SHELL` are redirected to a real OHOS shell.
- The shared profile hardcodes `tools.build:compiler_executables` to
  `/data/service/hnp/bin/clang`, which is absent on this worker. The recipe
  resolves CC/CXX via the profile conf, falling back to `shutil.which("clang")`
  when the configured path is not a real file (matches libxext/6.4.0).

## Upstream tests

- `tests/Makefile.am` lists 8 `check_PROGRAMS` but only 7 `TESTS`:
  cxslist-test, cxlist-test, cxtree-test, cxmap-test, cxstring-test,
  cxdeque-test, cxtypes-test. `cxmessages-test` is built but not registered in
  `TESTS`, so `make check` runs 7 tests.
- The host is native aarch64 OHOS (`/bin/sh` is an aarch64 musl ELF), so the
  built aarch64 test binaries execute directly — no emulator or cross-run.

## test_package

- Links `libcext`, creates a `cx_string`, formats into it, reads length/content
  back, exercises `cx_slist` push/front/pop with state assertions, and reads
  the `CX_VERSION_*` compile-time symbols. 5 assertions with return-code state
  changes.
