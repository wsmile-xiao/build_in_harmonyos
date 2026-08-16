# alpm-repo 0.1.2 HarmonyOS PC notes

## Software

The `alpm-repo` task packages the upstream `alpm-repo-db` Rust crate. It
provides a library plus two command line tools for ALPM repository sync
database member files:

- `alpm-repo-desc`
- `alpm-repo-files`

## Porting

- Source is the official crates.io `alpm-repo-db-0.1.2.crate` archive.
- The recipe enables the upstream `cli` feature and builds with Cargo.
- Cargo uses the upstream `Cargo.lock` with `--locked`.
- On OHOS/Linux, clang is selected as the Rust linker.
- On old-port OHOS, the recipe bootstraps Rust from Harmonybrew Rust,
  OpenSSL, and zlib bottles with Python urllib because `curl`/Harmonybrew are
  not available by default.
- On old-port OHOS, Cargo uses an executable `clang-15` linker path plus OHOS
  sysroot/code-sign linker flags instead of the non-executable clang wrapper.
- The package installs both CLI binaries into `bin/`.

## Rust toolchain note

The upstream crate declares `rust-version = 1.85.0`, but the published
`Cargo.lock` resolves `time 0.3.47`, whose source requires Rust 1.88 APIs.
An unmodified build therefore needs Rust 1.88 or newer. Harmonybrew's OHOS
Rust bottle is newer than that.

The Windows local validation in this workspace used Rust 1.85.1 plus a
temporary `.tmp` vendored dependency compatibility shim to verify the package
recipe without modifying the upstream source archive or the port files.

## Upstream tests

The upstream Cargo suite includes 81 lib/bin/integration tests under:

- `src/desc`
- `src/files`
- `tests/files_cli.rs`
- `tests/integration.rs`
- `tests/parse_errors.rs`

On Windows, three tests are skipped because they assert Unix absolute-path
and slash formatting semantics. OHOS/Linux runs the full command without
those Windows-only skips:

```sh
cargo test --release --locked --features cli --no-fail-fast --lib --bins --tests
```

OHOS aarch64 old-port validation ran the full command with no skips:

- `src/lib.rs`: 37/37 passed
- `src/bin/alpm-repo-desc.rs`: 0/0 passed
- `src/bin/alpm-repo-files.rs`: 0/0 passed
- `tests/files_cli.rs`: 21/21 passed
- `tests/integration.rs`: 14/14 passed
- `tests/parse_errors.rs`: 9/9 passed
- Total: 81/81 passed

## test_package

The test package verifies that both installed binaries exist and can execute
their top-level and `validate` help paths:

- `alpm-repo-desc --help`
- `alpm-repo-desc validate --help`
- `alpm-repo-files --help`
- `alpm-repo-files validate --help`

## OHOS old-port CI result

- Port: old port 56267
- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-0.1.2-alpm-repo-0.1.2-oldport-r1-20260815-conan-20260815-231444-56188`
- Recipe revision: `0e53282014ae298e780c3d3252596757`
- Package revision: `01a5b495a3ec228bab4ece2283501e0f`
- `cargo build --release --locked --features cli`: passed
- `cargo test --release --locked --features cli --no-fail-fast --lib --bins --tests`: 81/81 passed
- `test_package`: 4/4 CLI help checks passed
- CI gates: L0/L1/L2/L4/L5 passed
