# libmacaroons 0.3.0 adaptation notes

## Current status

Recipe builds the official `releases/0.3.0` GitHub archive (sha256
`e1db403c01b0407a276a84b2aaf54515faebe1a5c1a31ec10857a1917161d109`)
on HarmonyOS aarch64 by compiling the upstream C sources directly with
a capability-probed device compiler (PATH-first `cc`/`clang`, profile
absolute hnp path only as verified fallback). The archive ships only
`configure.ac` / `Makefile.am` (no pre-generated `configure`); the
autotools bootstrap chain is unusable on device, so the recipe does not
run autoreconf and has zero tool_requires. Real pass counts come from
the device preflight log.

## Source audit (corrected 2026-09-14)

Earlier rounds assumed 12 C sources (`slice.c`, `v1.c`, `v2.c`,
`varint.c`, ...) and 39 TESTS entries (`test/varint`,
`test/unit/*.vtest`). That was wrong — it describes a different
macaroons implementation. The actual upstream file list at
`releases/0.3.0` (verified via GitHub API + `Makefile.am`):

- Library: `libmacaroons_la_SOURCES = base64.c macaroons.c packet.c
  port.c` — exactly 4 files. There is no `slice.c`, `varint.c`,
  `v1.c`/`v2.c`, `tweetnacl.c`, or `sha256.c` in this archive.
- Hard dependency: `libsodium >= 0.4` (`PKG_CHECK_MODULES` in
  `configure.ac`); `port.c` wraps sodium HMAC/secretbox/randombytes
  (`sodium/crypto_auth_hmacsha256.h`,
  `sodium/crypto_secretbox_xsalsa20poly1305.h`, `sodium/utils.h`,
  `sodium/randombytes.h`). Satisfied by vendored libsodium 1.0.20
  (see below); optional python bindings / JSON support default OFF.
- No libbsd usage anywhere in `configure.ac`/`Makefile.am`; the old
  libbsd narrative in these notes was incorrect and is dropped.
- `macaroons.c` has no `#error portability problem` marker; no patching
  needed.
- Optional python bindings / JSON support default OFF; not enabled.

## Vendored libsodium (2026-09-14, 3rd-strategy-cycle new route)

Why the previous pin no longer holds: preflight log for 1.0.20 shows
`Checking remote: conancenter` then `Downloaded recipe revision ...
from conancenter`, followed by `Main binary package missing` and an
on-device `configure[139]: /data/service/hnp/bin/bash: inaccessible`.
So conancenter carries the 1.0.20 recipe too and shadows ohpcd in the
dual-remote preflight; the "1.0.20 is ohpcd-only" assumption is
refuted by the log. Any `requires("libsodium/...")` reintroduces the
same shadowing + hnp-bash + read-only-/tmp failure, regardless of
version. Prior cycles (absolute-path probe, source-list fix,
version pin) all kept the external edge and therefore could not
recover; this round removes the edge instead.

New route (E277 staging pattern, single-package PR): `requirements()`
is empty. The official libsodium-1.0.20 release tarball
(`https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz`,
sha256 `ebb65ef6...d30ce19`, identical to `archives/l/libsodium`
upstream) is declared as conandata `sodium` entry, fetched in `build()`
to `build_folder/sodium_src` (source() only fetches libmacaroons), and
built to
`build_folder/sodium_prefix` via `sh ./configure --disable-shared
--enable-static --disable-dependency-tracking` + `make -j1` +
`make install`, driven by `/bin/sh` (HMBS shell, never the profile hnp
bash), HMBS `TMPDIR`, probed `CC`/`AR`, and the repo's umask-022
relaxation. Only the temp-dir root is changed; tests are untouched.
2026-09-14 fix: vendored `configure` died at
`./build-aux/config.guess: unable to guess system type` /
`configure: error: cannot guess build type` because the 2022-01-09
`config.guess` does not know HarmonyOS `uname`. The recipe now applies
the same in-code edits as `archives/l/libsodium/1.0.20` patches
0001 (HarmonyOS `uname` -> `*-unknown-linux-ohos`) and 0002
(`config.sub` accepts `linux-ohos`) to every `config.guess`/`config.sub`
under the vendored tree before running `configure`, so the native device
build guesses natively. No `--build`/`--host` flags are passed (native
build; forcing them would falsely mark `cross_compiling=yes` per
P-AUTOTOOLS-001).
Main sources compile with `-I<staging>/include -L<staging>/lib
-lsodium`; `package()` ships `libmacaroons.a/.so` plus vendored
`libsodium.a` and sodium headers; `package_info` libs are
`["macaroons", "sodium"]` with no external requires. Crypto bytes are
untouched upstream libsodium code, proven by the 4 HMAC vectors plus
the consumer round-trip/verify below.

## Upstream tests (corrected)

`Makefile.am` TESTS with default options is a single entry:
`test/python-hmac-sanity-check.sh`, which runs
`python2 -m doctest test/python-hmac-sanity-check` (4 HMAC-SHA256
vectors with hard-coded digests; `test/readme.sh` is commented out of
TESTS). The device has python3 only, so the recipe runs a faithful
python3 port: byte-identical inputs, the same 4 expected digests, each
digest additionally cross-checked verbatim against the upstream test
file (stale-port guard), PASS counts parsed from the script output
(`HMBS_UPSTREAM_TEST_RESULT`, framework `doctest`, discovered=4).

## Consumer test

`test_package/test_macaroons.c` uses the real C API only:

1. `macaroon_create` returns non-NULL and validates (`macaroon_validate == 0`)
2. `macaroon_add_first_party_caveat` + serialize/deserialize round-trip
   preserves equality (`macaroon_cmp == 0`)
3. `macaroon_verifier_create` + `satisfy_exact` + `macaroon_verify`
   authorizes the caveated macaroon

Built against the installed package (vendored sodium included) and run
on device; `test()` emits `HMBS_TEST_PACKAGE_RESULT` with
discovered=3/passedCount=3 (PASS-line counts parsed from the consumer
log, not hard-coded).

2026-09-14 fix: test_package previously used CMakeToolchain +
cmake_layout, which fails on device (cmake 4.4.3 has no
Platform/HarmonyOS.cmake: "System is unknown to cmake" plus
CMAKE_C_COMPILER check failure on the profile hnp path, compounded by
read-only /tmp). Rewritten to the proven direct-cc pattern from
archives/l/libsodium/1.0.20 (basic_layout, compile with
tools.build:compiler_executables cc + -lmacaroons -lsodium, HMBS
TMPDIR/TMP/TEMP via generate(), stdout captured to build_folder and
PASS: lines counted). test_package/CMakeLists.txt is now unused.

2026-09-14 fix (round 2): test_macaroons.c used wrong signatures from a
different macaroons implementation (MACAROON_V2 version arg,
macaroon_error(), 3-arg deserialize). Rewritten against the real
releases/0.3.0 macaroons.h: 1-arg size hint, 0/-1 serialize without
version, 2-arg deserialize of the NUL-terminated base64 string, err
printed as int. Three checks preserved (create/round-trip/verify).

## Falsifiability guard

- Missing upstream sources fail fast with the actual `source_folder`
  listing (no silent empty build); missing vendored `configure` or
  missing `libsodium.a` after install likewise aborts with the listing.
- The sanity script exits non-zero on any vector mismatch; an empty
  upstream test file or a digest absent from it aborts before running.
- Consumer asserts are real API calls; a stub binary returning 0 would
  fail at `macaroon_create`/link time, not pass silently.
- Vendored sodium is exact upstream 1.0.20 code (SHA-pinned); HMAC
  vectors prove byte-compatibility, consumer round-trip/verify proves
  secretbox linkage.
