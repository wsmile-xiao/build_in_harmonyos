# libgcrypt 1.12.2 HarmonyOS PC adaptation notes

## Scope

- Dependency Issue: `OpenHarmonyPCDeveloper/build_in_harmonyos#1269`.
- Downstream: Percona XtraBackup Issue `#1088`.
- Official source and SHA-256 match Homebrew and GnuPG upstream.
- Only Conan dependency: `libgpg-error/1.55`.

## Adaptation decisions

- Preserve the standard Conan shared/static option contract.
- Use AutotoolsToolchain triplets; do not append a fake Linux/musl
  `--build` or `--host` manually.
- Patch `config.guess` and `config.sub` to recognize HarmonyOS.
- Keep `configure.ac` as the libgpg-error version source of truth. Because the
  release tarball ships `configure` and CI does not regenerate it, mirror that
  single version value with an exact recipe-time replacement.
- Replace only the two failing generated `configure` temporary-directory
  umasks at recipe time for HMDFS. Exact-match failures are blocking; no broad
  generated-file patch or ignored configure error is used.
- Accept libgpg-error 1.55 after confirming that its published headers export
  the gpgrt APIs used by libgcrypt 1.12.2; full build and regression tests are
  the compatibility gate.
- Mirror Homebrew's portable `--disable-asm` configuration and prebuild the
  jitterentropy objects with `-O0` instead of disabling that entropy source.
- Run the complete upstream `make check` suite in every Conan build.
- Run the three generated shell test entries through `CONFIG_SHELL` on HMDFS;
  the wrapper uses POSIX `set -eu`, and all ELF test entries remain direct
  Automake tests.
- Use `/system/bin/sh` for the make/install phase so recursive Libtool archive
  paths do not depend on bash recovering `getcwd()` from HMDFS.
- Propagate libgpg-error headers/libs with Conan requirement traits because
  `gcrypt.h` publicly includes `gpg-error.h`.
- Remove Libtool hardcoded build paths before linking, remove packaged `.la`
  metadata, clear RPATH defensively, and re-sign every packaged OHOS ELF.

## Existing knowledge used

- `E007`: Autotools `config.guess`/`config.sub` HarmonyOS recognition.
- `E087`: HMDFS shell scripts require an explicit shell interpreter.
- `E129`: Autoconf `umask 077` temporary directories are not writable on HMDFS.
- Global notes: `openharmony-pc-autotools-patchng-hmdfs`,
  `openharmony-pc-conan-library-shared-options`, and
  `openharmony-pc-conan-test-virtual-run-env`.

No new project knowledge entry is needed; the observed failure modes are
already covered by the entries above.

## HarmonyOS PC validation

- Device: HarmonyOS PC, AArch64, Clang 15.0.4, Conan 2.29.1.
- Shared and static `conan create` both returned 0.
- Upstream independent tests: 41 total, 39 PASS, 2 SKIP, 0 FAIL.
- Skips: upstream-disabled 6 GiB and 256 GiB large-data hash tests.
- The installed consumer passed 15 independently runnable public-API commands
  in both linkage modes: version negotiation; SHA-256, SHA-512, SHA3-256;
  HMAC-SHA256 and CMAC-AES; AES-128 ECB encrypt/decrypt; AES-256 CBC;
  ChaCha20; PBKDF2-SHA256; MPI add/mod; S-expression parsing; and nonce
  generation. Clang compiled the consumer with `-Wall -Wextra -Werror`.
- Shared and static CLI tools (`hmac256`, `dumpsexp`, `mpicalc`, and
  `libgcrypt-config` through bash) ran on the device.
- Shared package contains only `.so` library artifacts; static contains only
  `libgcrypt.a`. Both include licenses and no `.la` files.
- Shared SONAME is `libgcrypt.so.20`; no RPATH/RUNPATH or Conan cache string
  remains in the library. All packaged ELF files contain `.codesign`.
- The official source archive was transferred to the device because direct
  access to `gnupg.org` stalled. The device recomputed the official SHA-256
  before a localhost-only validation URL was used; the committed recipe keeps
  the official URL unchanged.

The logical test inventory is 41 upstream entries plus 15 installed-package
consumer commands. Of these, 54 passed and the two upstream 6 GiB/256 GiB hash
entries reported their configured SKIP status. Assertions and repeated
shared/static executions are not counted again, so the dependency exceeds the
50-passing-case threshold for the 1-point tier.

## Status

Built and validated locally on HarmonyOS PC; not uploaded or published.
