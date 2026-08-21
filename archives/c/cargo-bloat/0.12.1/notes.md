# cargo-bloat 0.12.1 HarmonyOS adaptation record

## Scope

- issue: 215 (original task; no new issue created)
- branch: `feat/cargo-bloat-0.12.1-215`
- worktree: `D:\harmonyos\worktrees\cargo-bloat`
- source: GitHub tag archive `v0.12.1`
- source SHA256: `8195cebb94a740cd3b89611ae79d7d3e2d8fd8ec297f5a0f07efa7069ef05be7`
- changed paths: the version directory plus the software-level `archives/c/cargo-bloat/commands.json` required by R38

## W0 and toolchain

`Cargo.toml` and `Cargo.lock` contain Rust crate dependencies only; no Conan dependency split was needed. The HarmonyOS base image had no `cargo` or `rustc` in PATH. The recipe now uses a checksum-pinned, OHOS-only fallback in the isolated Conan build folder:

- Rust 1.97.1 arm64 OHOS bottle
- OpenSSL 3.6.3, zlib-ng, and CA certificate bottles
- SHA256 verification for every bottle
- repair of the Harmonybrew `cargo` wrapper to the unpacked `cargo.real`
- explicit `CARGO`, `RUSTC`, `LD_LIBRARY_PATH`, Cargo rsproxy, and OHOS clang linker settings

No toolchain files are installed into the device image or user home. The test package uses the same isolated fallback and copies `cargo.real` to the runner temporary directory because the device rejects execution of wrapper/ELF files under the source worktree. The temporary shim directory is removed when the test script exits, including assertion failures.

## Source/build analysis

- Build system: Cargo, edition 2018.
- Output: one CLI ELF at `target/aarch64-unknown-linux-ohos/release/cargo-bloat` on OHOS.
- Upstream checks: `cargo build` and `cargo build --no-default-features`.
- The installed executable is a Cargo subcommand and must be invoked as `cargo-bloat bloat` (or `cargo bloat`).
- `test_package` uses a dependency-free Rust fixture and exercises ELF parsing through `--crates --message-format json`.

## Verification

The 2026-08-20 single-package runner task `cargo-bloat-0.12.1-create-r6-20260820` completed with exit code `0`:

```sh
conan create archives/c/cargo-bloat/0.12.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

Observed results:

- Rust fallback downloaded and unpacked on the HarmonyOS `aarch64` device.
- `cargo build --release --locked --target aarch64-unknown-linux-ohos` succeeded.
- Package produced `bin/cargo-bloat` and `licenses/LICENSE`.
- test_package passed version/help checks and fixture ELF analysis: `cargo-bloat version/help/ELF analysis checks passed`.

The repository-wide `ci/conan/build_and_test.sh` L0 R38 gate requires software-level CLI metadata. This PR includes `archives/c/cargo-bloat/commands.json` with `type: tool`, the `0.12.1` Conan reference, and `binary: true`.

The first AtomGit CI retry (`#28865`) passed R38, KC, and junk checks but reached Cargo with the worker's preinstalled Harmonybrew toolchain and failed rsproxy TLS verification because Cargo had no CA bundle configured. The recipe now resolves a system or Harmonybrew CA bundle for every toolchain path, writes Cargo `cainfo` plus `CARGO_HTTP_CAINFO`, and extracts the pinned CA bottle only when no usable bundle exists.

## Path B knowledge contribution

This submission uses Path A for the package recipe and Path B for the reusable HarmonyOS Rust toolchain knowledge. The contribution is the isolated, checksum-pinned toolchain fallback and the verified runner execution-policy workaround, not a claim that the upstream Rust source is intrinsically complex.

The complete r1-r6 failure evolution, root causes, reproduction command, and evidence boundary are recorded in `reports/path-b-evidence.md`.

## Next commands

For a future isolated run, use the same `ohos-test-runner.sh --try-lock` wrapper, an isolated `CONAN_HOME`, and `TMPDIR`; no global Rust installation is required because the recipe fallback is self-contained.
