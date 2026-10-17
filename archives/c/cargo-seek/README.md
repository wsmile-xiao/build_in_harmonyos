# cargo-seek

A terminal user interface for searching, adding and installing cargo crates.

## OHOS adaptation

- Pure Rust Cargo project, edition 2021, builds with `cargo build --release --locked`.
- Defaults to `aarch64-unknown-linux-ohos` on OHOS, overridable via `RUST_TARGET`.
- Uses checksum-pinned Harmonybrew Rust 1.97.1 plus OpenSSL, zlib, and CA bottles when the runner has no cargo/rustc.
- Package provides `bin/cargo-seek` (also usable as `cargo seek`).

## Dependencies

- Rust toolchain (cargo/rustc) via Harmonybrew fallback on OHOS; no Conan dependencies.

## References

- https://github.com/tareqimbasher/cargo-seek
- https://crates.io/crates/cargo-seek
