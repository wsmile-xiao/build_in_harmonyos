# KCodecs (KF5/Qt5) — kcodecs5

KDE Frameworks 5 string and text codec library (`libKF5Codecs.so`).

Provides base64, quoted-printable, uuencode, RFC2047 encoded-word handling,
HTML entity decoding and text encoding detection, built on top of Qt5Core
(`QTextCodec`).

## Versions

| Version | Status | Build date | Conan ref |
|---------|--------|-----------|-----------|
| 5.116.0 | published | 2026-09-25 | kcodecs5/5.116.0 |

## OHOS adaptation highlights

- `KF_IGNORE_PLATFORM_CHECK=TRUE` + `CMAKE_SYSTEM_NAME=Linux`
  (CMake 4.1 lacks a Platform/HarmonyOS module).
- `ecm_install_po_files_as_qm` disabled (Qt5LinguistTools not on ohpcd).
- No libiconv fallback needed (unlike KF6): Qt5's `QTextCodec` ships legacy
  charsets without ICU.
- Depends on qt5-qtbase/5.15.2 + ecm/6.20.0 (tool).

See [5.116.0/notes.md](5.116.0/notes.md) for the full adaptation log.
