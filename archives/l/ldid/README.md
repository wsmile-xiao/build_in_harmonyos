# ldid

[![License](https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg)](https://github.com/ProcursusTeam/ldid)

**ldid** (Link Identity Editor) is a Mach-O pseudo-codesigning tool from the
[Procursus](https://github.com/ProcursusTeam) project. It manipulates code
signatures, entitlements, and requirements on Mach-O binaries.

## Features

- Pseudo-signing with ad-hoc entitlements (`-S`)
- Hash type selection (SHA1/SHA256)
- Private key signing (PKCS#12)
- Entitlement extraction and merge
- Code signature inspection (`-h`)

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| libplist | 2.3.0 | Apple Property List parsing |
| openssl | 3.5.6 | Cryptographic functions (libcrypto) |

## Build

```bash
make CC=clang CXX=clang++ PREFIX=/usr/local
make install DESTDIR=/staging PREFIX=/usr/local
```

## Usage

```bash
ldid -S entitlements.xml file      # Pseudo-sign with entitlements
ldid -h file                       # Print signature info
ldid -K key.p12 -U password file   # Sign with private key
```

## License

AGPL-3.0-only
