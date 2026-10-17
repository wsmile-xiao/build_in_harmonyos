# libmcrypt

libmcrypt is a thread-safe symmetric encryption library used by the mcrypt
command line tools. The 2.5.8 release builds all algorithms and modes into the
library when dynamic module loading is disabled, which makes it suitable for a
static OHOS package.

## Features

- Uniform API for block and stream ciphers.
- Includes algorithms such as Rijndael/AES, Twofish, Blowfish, DES, 3DES,
  CAST, RC2, Serpent and XTEA.
- Supports cipher modes such as CBC, CFB, CTR, ECB, nCFB, nOFB, OFB and
  stream.

## OHOS Adaptation Notes

- The release uses old Autotools scripts, so `config.guess` and `config.sub`
  are patched for the `aarch64-unknown-linux-ohos` triplet.
- `configure` temp directory creation uses `umask 022` to avoid HMDFS-style
  permission failures.
- The Conan recipe removes stale Autotools outputs shipped in the release
  tarball before configuring.
- The OHOS build uses explicit LLVM binutils and a job-local shell for
  Autotools helpers.
- The package is built as a static library with dynamic module loading
  disabled, so no external module directory is needed at runtime.
- The OHOS true-device run passed upstream `ciphertest` and `aestest`, plus
  the Conan consumer `test_package`.

## Dependencies

No external Conan dependencies are required by libmcrypt itself.
