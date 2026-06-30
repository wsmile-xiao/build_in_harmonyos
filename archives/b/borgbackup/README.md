# borgbackup

BorgBackup (short: Borg) is a deduplicating backup program with compression and authenticated encryption.

## Description
BorgBackup is a efficient backup solution that supports deduplication, compression (lz4, zstd, zlib), and encryption. It is designed for efficient and secure backup of data.

## Dependencies
- Python 3.14+
- OpenSSL (libcrypto)
- liblz4
- libzstd
- libxxhash
- msgpack

## OpenHarmony Adaptation
- Cython multiprocessing forkserver fails on OpenHarmony/musl — must disable parallel cythonize
- OpenHarmony has no libacl — ACL features unavailable, use stub headers for compilation
- Python .so modules need ELF signing before dlopen can load them on HMDFS
- pip wheel build fails on OpenHarmony due to /lib/ld-musl permission — use `setup.py install` instead