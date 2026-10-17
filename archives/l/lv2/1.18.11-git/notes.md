# LV2 1.18.11-git adaptation notes

## Scope

- Package: `lv2/1.18.11-git`
- Issue: #594
- Source commit: `3c57dae`
- Source: `https://gitlab.com/lv2/lv2/-/archive/3c57dae/lv2-3c57dae.tar.gz`
- SHA256: `11b70869f1840d7365a884d9a9b3faf16dbe4642bb9171e257a18be63dd027ff`

## Adaptation

- Packages the public LV2 headers, specification bundles, and `lv2.pc`.
- Exposes the package as a Conan header library.
- The consumer test uses the compiler selected by the Conan profile. A cross
  build must provide `tools.build:compiler_executables[c]` explicitly.

## Tests

The exact source revision registers 29 Meson cases in the `build`, `unit`, and
`spec` suites. The native preflight enabled tests with documentation, tools,
and lint disabled, while retaining every independent runtime test.

The added `test_package` compiles and runs a minimal C consumer and verifies the
installed header, core bundle manifest, and pkg-config file. It contains one
consumer scenario with seven assertions.

## Local validation

- Upstream Meson suite: 29/29 passed; failed 0; skipped 0.
- Linux x86_64 `conan create`, Release: passed.
- Added consumer test: 1/1 passed; 7/7 assertions passed.
- The local Docker preflight is not an official OHOS armv8 CI result.
