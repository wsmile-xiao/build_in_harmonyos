# curl 8.15.0.1 HarmonyOS PC adaptation notes

## Scope

- Upstream source: curl 8.15.0 release archive (same source as 8.15.0).
- Version 8.15.0.1 is an adaptation fix release (R37) for the HMDFS log
  directory issue discovered during re-verification of 8.15.0.
- Formal package: shared libcurl plus the curl command-line executable.
- Declared Conan dependencies: `openssl/3.5.6.1` and `zlib/1.3.1.1`.
- Optional libpsl, nghttp2, libssh, libidn2, Brotli, Zstd, GSSAPI, LDAP,
  RTMP, c-ares, and HTTP/3 libraries are disabled.

## Dependency status

The earlier W0 blocker is resolved. OpenSSL PR #3047 merged on 2026-08-03.
On 2026-08-04, a fresh Conan home on HarmonyOS PC downloaded both required
recipes directly from `ohpcd`:

- `openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801`
- `zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9`

The shared libcurl recipe uses zlib 1.3.1.1 because its static objects are
compiled with `-fPIC`.

## Header compatibility

The previous archive carried a corrupt patch that replaced four preprocessor
conditions with `#if 0`. It is removed. curl's CMake project already exposes
`HAVE_LINUX_TCP_H`, and the HarmonyOS configuration sets it to `OFF`, selecting
`netinet/tcp.h` without modifying upstream source. This follows existing
knowledge E091 and E119 for the OHOS `sockaddr_storage` header conflict.

## Upstream tests

The source contains 1,849 numbered data test definitions, 57 unit C sources,
4 tool-unit C sources, 231 libtest C sources, plus client and server helpers.
The recipe builds the aggregate `testdeps` target. It runs `runtests.pl` only
when Conan reports that target binaries are runnable; Windows-to-OHOS builds
record compilation and linking only.

The terminal `conan create` ran natively on an AArch64 HarmonyOS PC against
commit `0f2ccb7baa1e7eb83ffc7abb8a8c9aa062870820`. The upstream runner considered
1,849 tests: all 1,556 runnable tests passed and 293 were skipped by upstream
feature or server-capability checks. No test failed. The Conan consumer linked
and executed, reporting curl 8.15.0 with OpenSSL 3.5.6 and zlib 1.3.1.

The final package contains 532 regular files, no static archives, and no
Windows path residue. The build-tree and package-tree hashes are identical for
both `curl` and `libcurl.so`, confirming that installation did not rewrite the
signed ELF files. Both files retain `.codesign` sections and use the expected
`$ORIGIN/../lib:$ORIGIN` RUNPATH. The device log SHA256 is recorded in the
version manifest so the local validation evidence can be checked independently.

## Contest path

- Path A: migrate the old manifest-only archive to a Conan 2 recipe.
- Paths B/C are not claimed by Issue #1287. If a later technical review finds
  either path applicable, the Issue title and application material must be
  updated before the PR description claims it.
**版本说明**: 8.15.0.1 = 8.15.0 + HMDFS log directory fix (R37)
---

**编译结束**: 2026-09-07 23:16
**最终状态**: built
