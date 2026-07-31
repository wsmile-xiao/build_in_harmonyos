# libmcrypt 2.5.8 upstream tests

Date: 2026-07-30

## Release test inventory

The release source registers 2 Autotools tests in `src/Makefile.am`:

- `ciphertest`
- `aestest`

`ciphertest` enumerates libmcrypt algorithms and modes, runs each algorithm
self-test, and verifies encryption/decryption roundtrips. `aestest` verifies
Rijndael-128/AES vectors for CFB, nCFB, nOFB and CTR modes.

## OHOS execution status

Passed on OHOS true-device runner. The Conan recipe runs the upstream test
suite during `build()` with:

```sh
make -j1 check
```

Run:

`/storage/Users/currentUser/ohos-test-runs/codex-a-libmcrypt-libmcrypt-2.5.8-conan-r8-newport-libadd-expand-20260730-142520-24217`

Result:

- Passed: 2
- Failed: 0
- Not run: 0

Observed upstream output:

- `PASS: ciphertest`
- `PASS: aestest`
- `All 2 tests passed`

## Added consumer test

The Conan `test_package` builds and runs a C consumer that links
`libmcrypt::libmcrypt`, opens `rijndael-128` in CBC mode, encrypts one block,
decrypts it, and checks that the original plaintext is restored.

OHOS result: 1/1 passed.

Observed output:

`libmcrypt aes-cbc roundtrip ok`

The CI runner also performed the destructive negative check and confirmed the
test genuinely depends on the packaged `libmcrypt` headers/library.
