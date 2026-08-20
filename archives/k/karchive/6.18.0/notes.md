# karchive 6.18.0 notes

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`karchive/6.18.0` package directory without modifying other KF package
recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_FUZZERS=OFF` keeps fuzz targets out of the baseline package build.
- `WITH_BZIP2=OFF` avoids linking the current local static `bzip2/1.0.8`
  archive into the shared KF library because that recipe does not guarantee
  PIC objects.
- `WITH_LIBZSTD=OFF` avoids the upstream zstd probe because it requires host
  `pkg-config`, which is not available on the current OHOS runner.
- `WITH_LIBLZMA=ON` and `WITH_OPENSSL=ON` keep xz/lzip and encrypted archive
  support using the current local `xz/5.6.2` and `openssl/3.5.6.1` packages.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- A minimal test-only MIME database is generated under the build folder and
  exposed through `XDG_DATA_DIRS` so upstream `kfiltertest` can resolve
  gzip-derived MIME inheritance (`image/svg+xml-compressed`,
  `application/x-gzdvi`) and `KTar` can auto-detect gzip/xz/lzma/lzip
  compressed tar files by filename on the current runner.
- `patches/0001-src-cast-openmode-arg.patch` casts `QIODevice::OpenMode` values to
  `int` before passing them to `QString::arg()`, matching Qt 6.11's stricter
  `QString::arg()` overload constraints for `QFlags`.

## Verification

Local and OHOS checks:

- Upstream source SHA256 verified on the OHOS runner:
  `fa24f703aa799e4ff5b9cc2e4a628745912ebfcc9f0c6bb6d92106ff9e02e26f`.
- Source patch applied:
  `patches/0001-src-cast-openmode-arg.patch`.
- Local syntax and whitespace checks passed:
  `python -m py_compile conanfile.py test_package/conanfile.py` and
  `git diff --check`.
- OHOS low-pressure run:
  `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/karchive-r6.log`.
- Full package reference:
  `karchive/6.18.0#8dd9a9b4a5805de0465a33ef039f385c:6dd5356c2d84a932438252879e0f79927cee0a3d#0300b5201c634c0d59eea69a8f6eb766`.
- Runner gates:
  L0 pass, L1 pass, L2 skip (`no bin/ dir`), L4 pass, L5 pass.
- Upstream CTest passed 4/4:
  `karchivetest`, `kfiltertest`, `klimitediodevicetest`,
  `kcompressiondevicetest`.
- `test_package` passed 1/1 and printed
  `PASS: KTar gzip write/read OK`.

## Upstream Tests Not Run

- `tests/kartest`, `tests/ktartest`, `tests/krcctest`, `tests/kziptest`, and
  `tests/k7ziptest` were built, but upstream marks them with
  `ecm_mark_as_test()` and does not register them as CTest entries; they are
  manual helper executables, not part of the upstream CTest run.
- `autotests/ossfuzz/*` was not built or executed because the baseline recipe
  sets `BUILD_FUZZERS=OFF`; those fuzz targets are not normal package
  verification tests.
- The AppStream metadata check was not set up because the current OHOS runner
  does not provide `appstreamcli`.
- BZip2 optional branches were not built or executed because `WITH_BZIP2=OFF`;
  the current local `bzip2/1.0.8` package is static and does not guarantee PIC
  objects for linking into shared `libKF6Archive.so`.
- Zstd optional branches were not built or executed because `WITH_LIBZSTD=OFF`;
  the upstream zstd probe requires host `pkg-config`, which is missing on the
  current OHOS runner.
