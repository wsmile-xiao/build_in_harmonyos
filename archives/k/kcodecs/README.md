# KCodecs

KCodecs is the KDE Frameworks 6 string and text codecs library. It provides
base64 / base45 / uuencode / quoted-printable transfer encodings, RFC2047
encoded-word decoding for mail headers, email address parsing/validation
(KEncodingProber charset detection built on the universal charset
detector), and KCharsets helpers on top of Qt6Core.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- qtbase on OHOS is built without ICU, so `QStringDecoder` cannot decode
  some RFC2047 legacy charsets (e.g. ISO-8859-8, GB2312 legacy names). The
  recipe adds a libiconv-based decode fallback (`decodeWithIconv`) wired in
  through the `KCODECS_ICONV_LIBRARY` CMake variable.
- `ECM_MODULE_PATH` is set manually and `conan_cmakedeps_paths.cmake` is
  written by the recipe because the CMakeDeps-generated ECMConfig.cmake
  does not propagate the variable, and qtbase uses `cmake_find_mode=none`.
- The recipe prepends `/system/lib64` to `LD_LIBRARY_PATH` for the cmake
  configure/test runtime so the compatible `libc++_shared.so` wins over
  the sandbox one (kconfig 6.26.0 precedent).

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0)
- Runtime/compile: qtbase (Qt6Core), libiconv (legacy charset fallback)

## References

- Homepage: https://invent.kde.org/frameworks/kcodecs
- Sources: https://download.kde.org/stable/frameworks/6.26/kcodecs-6.26.0.tar.xz
