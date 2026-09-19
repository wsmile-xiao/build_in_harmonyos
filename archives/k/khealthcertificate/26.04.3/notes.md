# khealthcertificate 26.04.3 notes

## Scope

KDE PIM health certificate parsing and verification library, part of the
KDE PIM chain. Required by downstream consumers (e.g. KDE Itinerary)
that display digital COVID-style vaccination/test/recovery certificates.

## Build shape

- Core library: `libKHealthCertificate.so` (EU DGC / Divoc / ICAO VDS /
  NL CoronaCheck / SHC parsers, OpenSSL signature verification, zlib
  compressed-data decoding)
- QML plugin: `lib/qml/org/kde/khealthcertificate/libkhealthcertificateqmlplugin.so`
  (built from src/qml against Qt6::Qml from the published
  qtdeclarative/6.11.1 split package; knewstuff pattern with
  QT_ADDITIONAL_PACKAGES_PREFIX_PATH)
- The upstream `health-certificate-decode` development CLI and the
  `tests/` decoder utilities have **no install rules** upstream
  (src/cli/CMakeLists.txt only does add_executable), so the package is a
  pure library package - no commands.json, no bindirs.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog processing
  (lconvert not available, kmime/knewstuff precedent).
- `BUILD_TESTING=ON` runs the 5 upstream QTest autotests via ctest.
- ECM 6.26 `KDEInstallDirs6` runs the qtbase qtpaths host tool during
  configure; `/system/lib64` is prepended to LD_LIBRARY_PATH so the
  musl loader resolves the compatible libc++_shared.so first (kconfig
  6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
- OpenSSL: static libcrypto.a from openssl/3.5.6.1
  (OPENSSL_ROOT_DIR + OPENSSL_USE_STATIC_LIBS, karchive pattern).
- ZLIB: static libz.a from zlib/1.3.2 via CMake's FindZLIB module
  (CMAKE_PREFIX_PATH injection).

## Upstream test data requirements (the two interesting findings)

1. `icaovdsparsertest` compares `country()` against 2-letter ISO 3166-1
   codes ("AU"). KF6::I18nLocaleData's KCountry resolves those at runtime
   from `iso-codes/json/iso_3166-1.json` via
   QStandardPaths::GenericDataLocation. OHOS has no /usr/share/iso-codes,
   so `iso-codes/4.20.1` is a **build (tool) requirement** whose
   `share/` tree is injected via XDG_DATA_DIRS in the test env
   (kfilemetadata shared-mime-info precedent). Without it: country()
   returns the raw 3-letter input ("AUS") and the test fails.
2. `nlcoronacheckparsertest` sets TZ=Europe/Amsterdam at startup
   (Q_CONSTRUCTOR_FUNCTION) and expects
   `QTimeZone("Europe/Amsterdam")` to be valid. OHOS ships no
   /usr/share/zoneinfo, so `tzdata/2026.3` (Python tzdata layout:
   lib/python3.12/site-packages/tzdata/zoneinfo) is a build (tool)
   requirement injected via TZDIR + QT_ZONEINFO (kcalendarcore 6.26.0
   precedent). Without it: "Unable to determine system time zone" and
   certificateIssueDate() comparisons fail.

Both data packages are tool_requires only: they are test-time data and
must not leak into the consumer graph / package_id.

## Verification

OHOS `conan create` verification passed on 2026-09-18.

- Full package reference:
  `khealthcertificate/26.04.3#18601fed84fde1b3b35a235788475e9a:a40d315666f16564a011542ac9539c298dc0e49c`
- Upstream CTest: 5/5 passed (divocparsertest, eudgcparsertest,
  icaovdsparsertest, nlcoronacheckparsertest, shcparsertest).
- Conan `test_package`: 1/1 passed (KHealthCertificateParser::parse
  smoke on an HC1 payload).
- self-signed 2 ELF files (libKHealthCertificate.so + QML plugin).

## Known caveats

- The KF6 published binaries embed build-tree-relative DT_NEEDED
  entries ("../../bin/libKF6XXX.so"); the test_package recipe mirrors
  the layout with a symlink farm at <build>/../bin and adds it to
  LD_LIBRARY_PATH (musl resolves relative NEEDED entries against each
  LD_LIBRARY_PATH entry).
