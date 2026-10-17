# serd 0.32.10 HarmonyOS adaptation notes

## Package scope

Serd is a lightweight C library for reading and writing RDF data, with the `serdi` command-line utility.

## Build configuration

- Meson build system.
- Static library by default to avoid target-side shared library signing/runtime loader surprises.
- `tools=enabled` keeps `serdi` available.
- `tests=enabled` and `build()` runs `meson.test()` for upstream verification.
- Documentation, man HTML, and lint are disabled because they require documentation/lint tooling that is not part of the library runtime.
- On OHOS, packaged `bin/serdi` is re-signed with `binary-sign-tool -selfSign 1` so it can run from the Conan cache during `test_package`.

## HarmonyOS validation

- `conan create archives/s/serd/0.32.10 --profile=ohos-aarch64 --build=missing`
- Upstream Meson tests run during `build()`.
- `test_package` builds a C consumer and runs packaged `serdi` on a Turtle input sample.

Result: passed on HarmonyOS aarch64.

- Upstream Meson tests: 65/65 passed.
- test_package: 2/2 passed (`serd_c_api` and `serdi_turtle_to_ntriples`).
