# bulletty

a pretty TUI feed reader (RSS+ATOM) that stores articles locally as Markdown files.

## OHOS adaptation

- Pure Rust Cargo project (edition 2024, rust-version 1.90), builds with `cargo build --release --locked`.
- Defaults to `aarch64-unknown-linux-ohos` on OHOS, overridable via `RUST_TARGET`.
- Uses checksum-pinned Harmonybrew Rust 1.97.1 plus OpenSSL, zlib, and CA bottles when the runner has no cargo/rustc.
- reqwest TLS backend switched from the default rustls stack (aws-lc-sys/BoringSSL does not cross-compile completely on OHOS) to `native-tls-vendored`, reusing the already-vendored OpenSSL; no TLS functionality is lost.
- Upstream unit test suite (73 `#[test]` cases) passes 73/73 on the OHOS cross-build.
- Package provides `bin/bulletty`.

## Dependencies

- Rust toolchain (cargo/rustc) via Harmonybrew fallback on OHOS; no Conan dependencies.

## References

- https://github.com/crocidb/bulletty
- https://crates.io/crates/bulletty