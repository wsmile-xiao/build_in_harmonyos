# Axel

Lightweight CLI download accelerator. Axel tries to accelerate the download
process by using multiple connections per file.

- Homepage: https://github.com/axel-download-accelerator/axel
- License: GPL-2.0-or-later
- Build system: autotools

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.17.14 | built | 2026-08-05 |

## OHOS Adaptation

- config.guess/config.sub patched for OHOS triplet detection
- compat-android.h extended for `__OHOS__` (musl pthread_cancel compatibility)
- configure umask 077 to 022 for HMDFS permission compatibility
- Depends on openssl/1.1.1w from Conan ohpcd remote
