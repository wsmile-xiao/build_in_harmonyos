# lzlib 1.16

- Upstream source: `https://download.savannah.gnu.org/releases/lzip/lzlib/lzlib-1.16.tar.gz`
- SHA-256: `203228de911780309dad6813e51541d7ea89469784f01cb661edba080ff1b038`
- Build: upstream custom `configure` script, `make`, then official `make check`; Conan stages the library and header.
- OHOS adjustment: the recipe maps the upstream `/bin/sh` shebangs in `configure` and `testsuite/check.sh` to `/system/bin/sh` for the device interpreter. Test logic is unchanged.
- Knowledge entry reused: E165 (`/bin/sh` shebang portability on OpenHarmony).

## Validation

- HarmonyOS device: `conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` — exit 0.
- Upstream suite: `make check` — 1/1 official suite passed. The output completed decompression, compression, and bad-input phases and ended with `tests completed successfully.`
- Consumer test: `test_package/test.c` — 9/9 checks passed, including the runtime API version and compression/decompression round trip.
- The package links successfully through `lzlib::lzlib` and contains the static library and public header.
