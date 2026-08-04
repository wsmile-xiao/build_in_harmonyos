mcrypt is a command-line encryption utility built on top of libmcrypt.

## Features

- Encrypts and decrypts files from the command line.
- Supports algorithms and modes exposed by libmcrypt.
- Can use mhash for hashing/key handling.

## OHOS adaptation

- Upstream uses Autotools.
- The recipe declares Conan requirements on libmcrypt, mhash, and zlib, and injects dependency include/lib paths for Autotools.
- `config.guess` and `config.sub` are patched through conandata-managed patch files for OHOS recognition.
- OHOS `config.status` temporary directory permissions are fixed through a formal conandata-managed patch.
- Current OHOS true-device validation passes on the new-port worker after building the dependency chain in the same Conan cache.
- `test_package` verifies `mcrypt --version`, stdin/stdout encryption/decryption, and file-path encryption/decryption roundtrips.
- The release source does not register official `make check` tests; see `2.6.8/reports/upstream-tests.md`.
- File-path mode is covered by the package-level test with an unambiguous file-before-key CLI order; upstream read-only stream flushes are removed by a formal patch.

## Dependencies

- libmcrypt
- mhash
- zlib

## References

- https://mcrypt.sourceforge.net/
- https://downloads.sourceforge.net/project/mcrypt/MCrypt/2.6.8/
