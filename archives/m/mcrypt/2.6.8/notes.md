# mcrypt 2.6.8 adaptation notes

## Status

Recipe structure and OHOS Autotools environment fixes are in place. The package builds and passes `test_package` on the OHOS new-port worker when `zlib/1.3.1`, `mhash/0.9.9.9`, and `libmcrypt/2.5.8` are available in the same Conan cache.

## Build approach

- Source: SourceForge release tarball `mcrypt-2.6.8.tar.gz`.
- Upstream build system: Autotools.
- Recipe strategy: declare Conan requirements on `libmcrypt/2.5.8`, `mhash/0.9.9.9`, and `zlib/1.3.1`, while also injecting dependency include/lib paths and optional `LIBMCRYPT_CONFIG`.
- `config.guess` and `config.sub` are patched through `patches/0002-ohos-triplet-and-file-mode-io.patch` when Conan applies `conandata.yml` patches.
- OHOS `configure` is invoked through the job-local shell and gets explicit LLVM `AR`, `RANLIB`, `NM`, `LD`, and `STRIP` tools.
- `patches/0003-ohos-configure-temp-umask.patch` relaxes Autoconf's local temporary-directory umask from `077` to `022` so `config.status` can write under OHOS setgid build directories.
- OHOS `/dev/random` and `/dev/urandom` support is left to upstream Autoconf detection; the recipe does not edit generated `config.h`.
- `patches/0002-ohos-triplet-and-file-mode-io.patch` also removes undefined `fflush()` calls on read-only input streams in file-mode close paths.
- OHOS `LIBMCRYPT_CONFIG` is executed through `/bin/sh <libmcrypt-config> --prefix=<package_folder>` to avoid direct execution permission issues in dependency package scripts.
- `package()` copies the built `src/mcrypt` to the build root before install so upstream `install-exec-hook` can create `mdecrypt`.
- `test_package` runs `mcrypt --version`, an encryption/decryption roundtrip over stdin/stdout, and an encryption/decryption roundtrip using file paths.

## Dependencies

- libmcrypt
- mhash
- zlib

## Verification

Windows is rejected by `validate()` because this package requires a POSIX target and target-side crypto libraries.

OHOS old-port r4 reached the dependency check before the dependency chain was available:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-mcrypt-mcrypt-2.6.8-conan-r4-llvm-tools-20260730-104946-25250`
- Lock: heavy `--try-lock`, acquired immediately.
- L0: pass.
- Result: `configure` failed with `*** libmcrypt was not found`.
- `config.log` shows `mcrypt.h` missing, and the worker has no `libmcrypt-config`, `mcrypt.h`, `libmcrypt.a`, `mhash.h`, or `libmhash.a` under `$HOME/usr/local`.

OHOS new-port r11 completed the dependency chain and mcrypt package validation after the final patch-file whitespace cleanup:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-mcrypt-mcrypt-2.6.8-newport-r11-chain-rev008d-20260731-163403-10827`
- Runner: new port `33332`, heavy `--try-lock`, lock wait 0 seconds, rc=0.
- Full ref: `mcrypt/2.6.8#008d0494b34271acf42d727094ead70b:8e6b4daae512b833db9495d8b0e8baa3acf64547#57cc24d5db5de60974d1af03950534d8`.
- Dependency refs consumed in the same job-local `CONAN_HOME`:
  - `zlib/1.3.1#90ec87a7f2894cf25103a42512d394d6:6b129b068851896169fae42d399fa922d239ce8a#9c9ba7bb9d5b88079ba56f57303339c9`
  - `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#3d98d49d3194718e8b5434e2493a3461`
  - `libmcrypt/2.5.8#2820bfa0ce1d46c81cbf222b30627530:21b17f8b2bc0e9511e276e3d57a23893067cefe5#9e537cb022689b229eccc56201e46c27`
- `test_package` output:
  - `Mcrypt v.2.6.8 (aarch64-unknown-linux-ohos)`
  - `mcrypt stdin/stdout roundtrip ok`

OHOS new-port r23 is the current validation after replacing runtime source rewrites with formal patches and adding file-path CLI coverage:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-2.6.8-mcrypt-2.6.8-local-r1-conan-20260731-224359-55995`
- Runner: new port `33332`, heavy `--try-lock`, lock wait 0 seconds, rc=0.
- Full ref: `mcrypt/2.6.8#1232e6d32243d0abac7c9ac8efcd04d8:8e6b4daae512b833db9495d8b0e8baa3acf64547#84ce92feec5cab317729dc0d43bd52b5`.
- Dependency refs consumed in the same job-local `CONAN_HOME`:
  - `zlib/1.3.1#90ec87a7f2894cf25103a42512d394d6:6b129b068851896169fae42d399fa922d239ce8a#9c9ba7bb9d5b88079ba56f57303339c9`
  - `mhash/0.9.9.9#974b33885624a6e6ddd418a702a32ebb:21b17f8b2bc0e9511e276e3d57a23893067cefe5#3d98d49d3194718e8b5434e2493a3461`
  - `libmcrypt/2.5.8#2820bfa0ce1d46c81cbf222b30627530:21b17f8b2bc0e9511e276e3d57a23893067cefe5#9e537cb022689b229eccc56201e46c27`
- `test_package` output:
  - `Mcrypt v.2.6.8 (aarch64-unknown-linux-ohos)`
  - `mcrypt stdin/stdout roundtrip ok`
  - `mcrypt file path roundtrip ok`

During recovery, `zlib/1.3.1` needed job-local environment exports for the new port: `CONFIG_SHELL=/bin/sh` and LLVM `AR/RANLIB/NM/STRIP/LD`. This was a dependency environment issue; no zlib files are part of this mcrypt package submission.

## Upstream tests

The 2.6.8 release source does not register official Autotools tests: no `TESTS`, `check_PROGRAMS`, or `check-local` entries were found in the release `Makefile.am`/`Makefile.in` files. Current official upstream test count is `0/0`.

Added package-level tests: `test_package/test_mcrypt.py` checks the installed binary version and verifies both stdin/stdout and file-path encryption/decryption roundtrips. The file-path test passes the file operand before `-k` because upstream `-k` accepts a variable-length key list.
