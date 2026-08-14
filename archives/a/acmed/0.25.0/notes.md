# acmed 0.25.0 adaptation notes

- Upstream tag: `v0.25.0`.
- Source archive SHA256: `e2d040a1910e40cc1915a794f31227a48dfd93fe1325e2857f6ed5780956d5c8`.
- The workspace is Rust/Cargo; the Conan package exposes the `acmed` daemon in `bin/`.
- The recipe enables upstream's `openssl_vendored` feature, producing a static OpenSSL build from the locked `openssl-src` Cargo crate. This avoids a separate Conan OpenSSL source download during CI.
- `build()` executes the upstream workspace test suite with the same vendored OpenSSL feature selection.
- The package test validates both the CLI version and configuration parser rejection of malformed TOML.
- Harmonybrew Rust is installed automatically when the CI worker has no Cargo toolchain.
