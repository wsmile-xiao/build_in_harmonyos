# libmcrypt 2.5.8 adaptation notes

## Status

OHOS true-device verification passed on 2026-07-30.

## Build Approach

- Source: SourceForge release tarball `libmcrypt-2.5.8.tar.gz`.
- Upstream build system: Autotools.
- Recipe strategy: build static `libmcrypt.a` and disable dynamic module loading.
- With dynamic loading disabled, the release build includes all upstream
  algorithms and modes in the library and does not need runtime module files.
- Stale Autotools outputs shipped in the release tarball are removed after
  source extraction.
- OHOS `configure` is invoked through the job-local shell and receives explicit
  LLVM `AR`, `RANLIB`, `NM`, `LD` and `STRIP`.
- OHOS `CPP` and `CXXCPP` are set explicitly because old Autoconf can otherwise
  fall back to `/lib/cpp`.
- Out-of-source OHOS builds add both source/build roots and include/lib
  directories because some algorithm modules include internal headers as
  `<lib/libdefs.h>`.
- The recipe copies `lib/libmcrypt.sym` into the out-of-source build `lib/`
  directory because upstream libtool links it through a cwd-relative
  `-export-symbols libmcrypt.sym` option.
- For out-of-source builds, the recipe mirrors module `.c` files into a
  build-local `lib/mcrypt_symb_sources/` directory and rewrites the generated
  `lib/Makefile` `mcrypt_symb.c` rule to read from that mirror. Upstream's
  original rule reads `../modules/.../*.c` relative to the build `lib/`
  directory, which otherwise creates an empty static preloaded module table
  when dynamic loading is disabled.
- The recipe also updates the generated `lib/Makefile` `libmcrypt_la_LIBADD`
  line from the generated `modules/*/Makefile` metadata. Upstream configure
  computes static module objects with cwd-relative `modules/.../*.c` probes,
  so out-of-source configure can otherwise leave `EXTRA_OBJECTS` empty even
  though the modules are built.

## Source Handling

No patch files are applied. The previous archive skeleton contained
config-script patch files, but those hunks did not apply cleanly to the
official tarball. The recipe now applies the same OHOS config.guess/config.sub
hooks and `umask 077` to `umask 022` fix programmatically before configure,
matching the working Autotools pattern used by mhash.

## Upstream Tests

The release source registers two official Autotools tests in `src/Makefile.am`:

- `ciphertest`
- `aestest`

The recipe runs `make -j1 check` after building. On the OHOS true-device
runner, both upstream tests passed:

- `ciphertest`: PASS
- `aestest`: PASS

Run directory:

`/storage/Users/currentUser/ohos-test-runs/codex-a-libmcrypt-libmcrypt-2.5.8-conan-r8-newport-libadd-expand-20260730-142520-24217`

## Consumer Test

The Conan `test_package` builds a C consumer against `libmcrypt::libmcrypt`.
It opens `rijndael-128` in CBC mode with built-in modules, encrypts one block,
decrypts it, and verifies the original plaintext is restored.

The OHOS test_package passed and printed:

`libmcrypt aes-cbc roundtrip ok`
