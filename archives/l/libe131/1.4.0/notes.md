# libe131 1.4.0

## Source

Upstream: https://github.com/hhromic/libe131 (release v1.4.0).

Release tarball (generated configure included):

- https://github.com/hhromic/libe131/releases/download/v1.4.0/libe131-1.4.0.tar.gz
- sha256: 3937ca6253b348788d8eaa41b562002e523358b34755bc4eb6353853b3e161d6
- size: 370587 bytes

Contents: configure, Makefile.in, config.guess/config.sub, m4/libtool,
src/e131.c, src/e131.h, examples/test_client.c, examples/test_server.c.

License: Apache-2.0 (LICENSE installed to licenses/).

## Build

Autotools, dependency-free (libc + sockets only).

- `AutotoolsToolchain` with `--prefix=/`.
- OHOS: `--build/--host=aarch64-unknown-linux-ohos`.
- shared default False (static); `--enable/disable-shared` toggled accordingly.
- Patches:
  - 0001 config.sub accepts `aarch64-*-linux-ohos`.
  - 0002 configure uses umask 022 for temp dirs (HMDFS).
  - 0003 configure clears a non-executable `CONFIG_SHELL` before the
    re-exec block (profile buildenv exports
    `/data/service/hnp/bin/bash`, inaccessible in the HMBS sandbox;
    `configure[159]` dies with "inaccessible or not found", exit 127).
    Source-level guard, independent of buildenv ordering.
- `generate()`/`build()`/`package()` force a probed writable TMPDIR
  (`HMBS_AUTOCONF_MKTEMP_FALLBACK` path > `HMBS_TMPDIR` >
  `HMBS_PLATFORM_CAPABILITIES.tmpdir` > `TMPDIR/TMP/TEMP`, excluding
  read-only `/tmp`, writability-probed, fallback
  `build-folder/.conan_tmp`) and a probed shell via
  `tc.environment()` + saved script + `os.environ` + on-disk
  `conanbuild*.sh` patch (courier-unicode/aldo precedent): prior rev
  only forwarded `TMPDIR/TMP/TEMP`, so when HMBS exposed the writable
  dir only via capabilities/fallback vars the compiler temp files fell
  back to `/tmp` (`C compiler cannot create executables`). `build()`
  adds a non-fatal `$CC --version` probe and a `config.log` tail dump
  on configure failure; `config.status` umask 022 fix re-applied post
  configure (HMDFS).
- OHOS compiler discovery (`_find/_ensure_ohos_compiler`, adapted from
  courier-unicode): prefer conf `tools.build:compiler_executables`
  only when the file exists, else `$CC/$CXX`, PATH clang, then SDK
  `llvm/bin` globs; override only `CC/CXX` exports via toolchain env +
  `os.environ` + `conanbuild*.sh` patch, never touching
  `CFLAGS/LDFLAGS`. 2026-09-15 preflight proved the profile
  `/data/service/hnp/bin/clang` absent
  (`/bin/sh: ... inaccessible or not found`), so the configure `CC`
  check failed independent of `/tmp`.
- `conandata.yml` lists the GitHub release URL behind
  `gh-proxy.com` first (CI `build_and_test.sh` GitHub mirror mapping),
  official URL last as fallback; `sha256` unchanged.
- `package()` removes `*.la` and installs LICENSE.

No `make check`: upstream Makefile.am defines no check/TESTS target.

## Upstream test audit

Audited the release tarball file list, configure.ac, Makefile.am, and
full-tree `*test*` names:

- No `tests/` or `test/` directory.
- No gtest (`TEST`/`TEST_F`), pytest (`def test_`), or ctest registration.
- `make -n check` has no rule; `make check` executes zero cases.
- `examples/test_client.c` / `test_server.c` are infinite-loop UDP
  sender/receiver demos needing live peers, not automated tests.

Declared `upstream_tests_exist: false` with audit in
`test_package/MANIFEST.yml`; test binary emits
`HMBS_UPSTREAM_TEST_RESULT status no_tests`.

## Tests

`test_package/test.c` (binary `test_libe131`) exercises the installed
library without network I/O:

1. `test_pkt_init` -- valid init, field oracles, 512-slot boundary.
2. `test_pkt_init_reject` -- NULL/universe/slot rejection.
3. `test_options` -- PREVIEW/TERMINATED set/get/toggle.
4. `test_validate` -- valid packet plus preamble/ACN-PID/DMP-type faults.
5. `test_dest` -- multicast/universe mapping, unicast 127.0.0.1, dest_str.
6. `test_discard_strerror_dump` -- sequence discard window, strerror, dump.

6 cases, 59 assertions. The binary prints `HMBS_TEST_PACKAGE_RESULT`
(discovered=6) and `HMBS_UPSTREAM_TEST_RESULT` (no_tests/0) from the
same counters; exit 0 only on all-pass.

Falsifiability: each check returns a distinct nonzero code; a stub
binary returning 0 without calling the library would not link
(`libe131::libe131` required) and empty outputs would fail the
packet-dump and string-equality oracles.
