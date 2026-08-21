# barcode 0.99

GNU Barcode 0.99 uses Autotools and ships a command-line program rather than
an installed public library. It is packaged as a Conan application.

The release archive has no automated upstream `TESTS` or `check_PROGRAMS`
suite, so it cannot provide upstream test cases. The consumer test instead
generates a Code 128 SVG and validates both SVG output and the input payload.

For OHOS, the 2013 bundled configure scripts are given portable GNU build and
host triplets. This only affects configure-time platform identification; the
Conan profile compiler remains the OHOS compiler.

HarmonyOS armv8 real-device validation passed with `conan create` exit 0.
The consumer test generated a Code 128 SVG with `-S -b 1234567890` and
verified both SVG markup and the encoded payload.

Reproduce with:

```bash
conan create archives/b/barcode/0.99 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
