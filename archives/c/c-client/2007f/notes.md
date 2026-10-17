# c-client 2007f OHOS Adaptation Notes

## Source
- URL: https://github.com/uw-imap/imap/archive/cab109466534e206a3652ef1c68fe88101b68bda.zip
- SHA256: aaca88c228b7bab9f73b5972e996fd39f770d8e226561b3e107ec19ceaf21570
- Provenance: conan-center-index c-client/2007f (cab10946)
- Mirror fallback: gh-proxy + github direct (build_and_test.sh handles)

## Build
- System: Makefile (top-level)
- Target: slx (Linux with OpenSSL, IP=6)
- Parallel: -j1 (HMBS jobs=1)
- SSL: openssl/3.5.8.1 via SSLDIR replacement (HMBS 2026-09-06 preflight: 3.5.6 resolves to conancenter recipe which rejects OHOS armv8/clang; 3.5.8.1 is OHOS-adapted published version with musl fd_set fix and lld libxml2 fix)
- Fix: ssl_unix.c include order for OpenSSL 3.x

## Upstream Tests
- No automated test suite. Top-level Makefile lacks 'check' target.
- Audited: grep make check, found only manual mtest tool.
- MANIFEST marks upstream_tests_exist: false with audit.

## Test Package
- 2 assertions: header inclusion + linkage
- Uses CMake to link c-client::c-client
- Emits HMBS_TEST_PACKAGE_RESULT JSON
