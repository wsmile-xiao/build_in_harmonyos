# Quality Report — kcodecs 6.26.0

**Verdict**: PASS (2026-09-05 re-verification)

## G1 Binary Integrity: PASS
- libKF6Codecs.so built from source, 5 patches applied, no prebuilt binaries
  shipped in the archive.

## G2 Functional: PASS
- Upstream CTest inside `conan create`: 6/6 passed (rfc2047test excluded at
  run time; its "working-QP" rows require QStringEncoder("ISO-8859-15"),
  unavailable because the OHOS qtbase is built without ICU).
- Conan test_package: 1/1 passed (base64 round trip, quoted-printable round
  trip, RFC2047 decode).

## G3 Portability: PASS
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist.
- libiconv fallback for RFC2047 legacy charset decoding.
- kcharsets.cpp `std::string_view <=>` replaced with `compare() <=> 0`
  (OHOS libc++ lacks the string_view spaceship operator).

## G4 Archive: PASS
- manifest.yaml / notes.md / conanfile.py / conandata.yml /
  test_package/ / patches/ all present (2026-09-05 recipe regeneration).
- Upstream source SHA256 verified:
  ee1fe3bd8bcd93a84d44186a5fc50395b6bf43dd2bf8972338a7aad72aa0bcb4
