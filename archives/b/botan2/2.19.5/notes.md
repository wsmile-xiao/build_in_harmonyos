# botan2 2.19.5

Botan 2.19.5 uses its bundled Python `configure.py` to generate a Makefile.
The recipe requests a static library, builds it, and executes the upstream
`make check` target before packaging the generated `libbotan-2.a` and
`include/botan-2` headers.

The consumer test links the package and computes the SHA-256 digest of a fixed
UTF-8 payload through `Botan::HashFunction`, providing a functional assertion
beyond checking that the archive exists.

## HarmonyOS validation (2026-08-21)

The OHOS `armv8` real-machine run completed successfully:

- `conan create` exited with code 0.
- `make -j1 check` completed 2,621,574 upstream Botan test assertions with
  `all tests ok`.
- The `botan2_sha256` consumer test passed through `ctest` (1/1).

The `0001-tests-tmpdir.patch` redirects the upstream POSIX test runner's
temporary file creation from `/tmp` to `TMPDIR` (falling back to the current
directory). This fixes the upstream `DataSinkFlush` test on OHOS without
platform-specific conditional compilation.

Reproduce the validation with:

```bash
conan create archives/b/botan2/2.19.5 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
