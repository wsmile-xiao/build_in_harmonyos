# kcodecs 6.26.0 notes

## Scope

KDE Frameworks 6.26.0 baseline of kcodecs (string/text codecs library,
libKF6Codecs.so), needed by the KF6 dependency chain (KF6 layer 2, task
#6324). Depends on qtbase/6.11.1 (Qt6Core), ecm/6.26.0 (ECM) and
libiconv/1.17 (legacy charset fallback).

## Adaptations

Same adaptation set as the 6.18.0 recipe, patches regenerated for 6.26.0:

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during the Conan
  build; `BUILD_FUZZERS=OFF` keeps oss-fuzz helper targets out.
- `ecm_install_po_files_as_qm(poqm)` is disabled (patch 0001) because the
  Qt Linguist tools component is not part of the OHOS qtbase package.
- libiconv fallback (patches 0002/0003): qtbase on OHOS is built without
  ICU, so QStringDecoder cannot decode some RFC2047 legacy charsets. The
  patches add an iconv-based decode fallback (`decodeWithIconv`) wired in
  via `KCODECS_ICONV_LIBRARY` when libiconv is present.
- ECM_MODULE_PATH set manually and `conan_cmakedeps_paths.cmake` written by
  the recipe because the CMakeDeps-generated ECMConfig.cmake does not
  propagate ECM_MODULE_PATH and qtbase uses cmake_find_mode=none.
- `/system/lib64` prepended to LD_LIBRARY_PATH for cmake/qtpaths runtime so
  the compatible libc++_shared.so wins over the sandbox one (kconfig
  6.26.0 / bluez-qt 6.28.0 precedent).

## Patch regeneration notes (6.18.0 → 6.26.0)

- Top-level CMakeLists.txt: hunk applies at the same place (QT deprecation
  version bumped 6.10.0 → 6.11.0 in context lines).
- src/CMakeLists.txt: 6.26.0 gained `target_compile_features(KF6Codecs
  PUBLIC cxx_std_20)` between `target_include_directories` and
  `target_link_libraries`, so the iconv hook block is inserted between the
  cxx_std_20 line and the Qt6::Core link line.
- src/kcodecs.cpp: parseEncodedWord now calls `QStringDecoder(defaultCS)`
  without `.constData()` (Qt 6.9 QStringDecoder ctor from QByteArrayView);
  the conversionCharset plumbing hunks were regenerated accordingly.

## Verification

- Upstream tarball SHA256 verified:
  `ee1fe3bd8bcd93a84d44186a5fc50395b6bf43dd2bf8972338a7aad72aa0bcb4`.
- All five patches verified with `patch -p1 --dry-run` against the
  unpacked 6.26.0 source.
- OHOS `conan create` verification passed on 2026-09-05:
  - Upstream CTest (inside conan create, BUILD_TESTING=ON): 6/6 passed
    (`codectest`, `base45test`, `kemailaddresstest`, `kcharsetstest`,
    `kencodingproberunittest`, `kencodingprobertest`). `rfc2047test` is
    excluded at run time: its "working-QP" rows expect
    `QStringEncoder("ISO-8859-15")` which the ICU-less OHOS qtbase cannot
    provide, so KCodecs falls back to the System codec ("Locale") and the
    expected encoded-word differs. Environment limitation, not a kcodecs
    regression (kconfig 6.26.0 exclusion-list precedent).
  - Conan `test_package`: 1/1 passed — base64 round trip,
    quoted-printable round trip and RFC2047 decode all verified.

## New upstream issues found in 6.26.0 (not present in 6.18.0)

1. `kencodingproberunittest` (new upstream test) does not link
   `KF6::Codecs`, so `target_compile_features(KF6Codecs PUBLIC cxx_std_20)`
   is not propagated to it and it compiles with `-std=c++17`, breaking
   `std::span` usage in `nsCodingStateMachine.h`. Patch 0004 adds an
   explicit `target_compile_features(kencodingproberunittest PRIVATE
   cxx_std_20)`.
2. `kcharsets.cpp` uses `std::string_view <=> std::string_view` which the
   OHOS libc++ (clang 15 toolchain) does not implement. Patch 0005
   replaces it with `compare() <=> 0` (built-in integer spaceship is
   available), preserving the `std::strong_ordering` return type.
3. `parseEncodedWord`'s `maybeCharset` is now a `QByteArrayView`; the
   iconv-fallback `conversionCharset` needs an explicit
   `QByteArray(maybeCharset)` conversion (patch 0003).
---

**编译结束**: 2026-09-05 22:03
**最终状态**: built
