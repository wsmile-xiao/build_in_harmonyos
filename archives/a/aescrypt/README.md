# aescrypt

Program for encryption/decryption using the AES (Rijndael) algorithm.

## Description

aescrypt is a simple command-line tool for encrypting and decrypting files using the AES (Rijndael) block cipher. It supports 128-bit, 192-bit, and 256-bit key sizes.

## Dependencies

No external dependencies. Only requires C standard library (musl libc on OHOS).

## OHOS Adaptation Notes

- Duplicate symbol fix: `int ROUNDS;` in rijndael.h was a tentative definition causing linker errors. Fixed by changing to `extern int ROUNDS;` in the header and adding `int ROUNDS;` definition in rijndael.c.
- Makefile `install` target doesn't support DESTDIR; manual staging directory creation is needed.
- No test suite available (no `make check` target).
- Software does not have `--version` flag; shows usage message when run without arguments.

## License

BSD-4-Clause
