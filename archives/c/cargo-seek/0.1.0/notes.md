# cargo-seek 0.1.0 HarmonyOS adaptation record

## Scope

- issue: cargo-seek 0.1.0
- branch: `feat/cargo-seek-0.1.0`
- source: GitHub tag archive `v0.1.0`
- source SHA256: `d2d9b63d2ef7fe56d3c9c5045350b991d443ed9ca56c28ed72168a88ba97009e`
- changed paths: the version directory plus the software-level `archives/c/cargo-seek/commands.json`

## W0 and toolchain

`Cargo.toml` edition 2021 with 30+ crates.io dependencies; no Conan dependencies. The HarmonyOS base image has no `cargo` or `rustc` in PATH. The recipe reuses the isolated, checksum-pinned OHOS-only fallback proven for cargo-bloat:

- Rust 1.97.1 arm64 OHOS bottle
- OpenSSL 3.6.3, zlib-ng, and CA certificate bottles
- SHA256 verification for every bottle
- repair of the Harmonybrew `cargo` wrapper to unpacked `cargo.real`
- explicit `CARGO`, `RUSTC`, `LD_LIBRARY_PATH`, Cargo rsproxy, and OHOS clang linker settings

No toolchain files are installed into the device image or user home. The test_package validates the installed binary via `--version`/`--help` and does not require a Rust fixture.

## Source/build analysis

- Build system: Cargo, edition 2021, `build.rs` with vergen-gix.
- Output: one CLI binary at `target/aarch64-unknown-linux-ohos/release/cargo-seek` on OHOS, also usable as `cargo seek` subcommand.
- Upstream checks: `cargo test --locked --all-features --workspace` (zero `#[test]` cases in 0.1.0), `cargo fmt --check`, `cargo clippy`, `cargo doc`. The recipe runs `cargo build --release --locked` as the build gate.
- The installed executable is `cargo-seek` in `bin/` and `licenses/LICENSE`.

## Verification

Expected local verification:

```sh
conan create archives/c/cargo-seek/0.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

Observed expectations:

- Rust fallback downloaded and unpacked on the HarmonyOS `aarch64` device when no host cargo is present.
- `cargo build --release --locked --target aarch64-unknown-linux-ohos` succeeds.
- Package produces `bin/cargo-seek` and `licenses/LICENSE`.
- test_package passes version/help checks: `cargo-seek --version` and `cargo-seek --help` contain expected flags (`--search`, `--fps`, `--help`).

The repository-wide `ci/conan/build_and_test.sh` R38 gate requires software-level CLI metadata. This PR includes `archives/c/cargo-seek/commands.json` with `type: tool`.

## Path A knowledge contribution

This submission uses Path A (basic adaptation). The contribution is the isolated, checksum-pinned toolchain fallback and verified OHOS build of a Rust TUI crate, following the cargo-bloat pattern without claiming upstream source complexity.
