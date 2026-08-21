# W0 report: cargo-bloat 0.12.1

## Result

The cargo-bloat 0.12.1 Conan recipe and test package were prepared and verified on the HarmonyOS `aarch64` device. The base image lacks Rust/Cargo, so the package supplies a checksum-pinned Harmonybrew fallback confined to the Conan build/test directories.

## Evidence

| Check | Result |
| --- | --- |
| Source URL | `https://github.com/RazrFalcon/cargo-bloat/archive/refs/tags/v0.12.1.tar.gz` |
| Source SHA256 | `8195cebb94a740cd3b89611ae79d7d3e2d8fd8ec297f5a0f07efa7069ef05be7` |
| Build target | `aarch64-unknown-linux-ohos` |
| Conan dependencies | None; Cargo.lock supplies Rust crates |
| Rust fallback | Rust 1.97.1 + OpenSSL/zlib/CA arm64 OHOS bottles, all SHA256 pinned |
| Device build | Passed: `cargo build --release --locked --target aarch64-unknown-linux-ohos` |
| Package smoke | Passed: `cargo-bloat bloat --version` and `--help` |
| Fixture ELF analysis | Passed: Cargo fixture, `--crates`, JSON output and filter |
| Runner task | `cargo-bloat-0.12.1-create-r6-20260820`, exit code `0` |

## Files prepared

- `archives/c/cargo-bloat/commands.json`
- `conandata.yml`
- `conanfile.py`
- `manifest.yaml`
- `notes.md`
- `reports/W0-report.md`
- `reports/path-b-evidence.md`
- `test_package/conanfile.py`
- `test_package/MANIFEST.yml`
- `test_package/test_cargo_bloat.py`
- `test_package/sample/Cargo.toml`
- `test_package/sample/src/main.rs`

## Scope note

The package changes remain in the version directory except for `archives/c/cargo-bloat/commands.json`, which is mandatory software-level CLI metadata under R38. It declares cargo-bloat as a tool and maps version `0.12.1` to `cargo-bloat/0.12.1` with a packaged binary.
