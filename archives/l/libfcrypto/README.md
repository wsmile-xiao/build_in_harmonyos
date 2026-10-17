# libfcrypto

Library for cryptographic primitives from the [libyal](https://github.com/libyal)
project. libfcrypto provides context-based implementations of the symmetric
ciphers used across the libyal toolchain — Blowfish, DES3, RC4 and Serpent —
plus the shared error/support helpers. It is a foundation dependency for other
libyal libraries such as libcaes.

- Upstream: https://github.com/libyal/libfcrypto
- License: LGPL-3.0-or-later
- Build system: Autotools (release archive ships generated `configure`)
- OHOS adaptation: see `0-20240414/notes.md` and `manifest.yaml`
