# caesiumclt 1.4.0 HarmonyOS adaptation record

## Scope

- branch: `feat/caesiumclt-1.4.0`
- source: GitHub tag archive `v1.4.0`
- source SHA256: `3dc4bc062536fcaa368d044aea873afd695feeabd9310d6118a7d45b2f0ad52e`
- changed paths: `archives/c/caesiumclt/1.4.0/` plus software-level `archives/c/caesiumclt/commands.json`
- applicant: `liucu`, team: `龙骑士`

## W0 and toolchain

`Cargo.toml` and `Cargo.lock` contain Rust crate dependencies only; no Conan
dependency split was needed. The recipe reuses the proven isolated Rust
fallback from `cargo-bloat/0.12.1` (same four SHA256-pinned Harmonybrew
`arm64_ohos` bottles: Rust 1.97.1, OpenSSL 3.6.4, zlib-ng-compat, CA
certificates), enabled only on OHOS inside the Conan build folder.

## Source/build analysis

- Build system: Cargo, edition 2021, Rust >= 1.79.0 upstream.
- Output: one CLI ELF `caesiumclt` at
  `target/aarch64-unknown-linux-ohos/release/caesiumclt` on OHOS.
- Upstream tests: `cargo test --locked`, 38 tests total:
  - `src/compressor.rs`: 6 (`test_compute_output_full_path`,
    `test_perform_compression`, `test_no_upscale_prevents_resize`,
    `test_build_resize_parameters`, `test_gif_quality_lossless_and_zero`,
    `test_min_savings_skips_files`)
  - `src/options.rs`: 9 (validators for quality/verbosity/png level/range,
    overwrite/format/chromasubsampling enums, max_size/min_savings)
  - `src/scan_files.rs`: 7 (extension/mimetype/base-folder/base-path/scan/progress)
  - `src/main.rs`: 16 (parallelism/progress/chroma/options/recap/stats/json variants)
- `build()` runs `cargo build --release --locked` then `cargo test --locked`,
  parses `running N tests` / `test result: ok. N passed` lines, and emits
  `HMBS_UPSTREAM_TEST_RESULT` with framework `cargo-test`. Any failure or
  incomplete run raises and fails the build.
- GitHub tag archive is used (not crates.io) because `Cargo.toml` excludes
  `samples/` from the published crate, while `test_perform_compression` needs
  `samples/j0.JPG`, `p0.png`, `w0.webp`, `t0.tif` and nested fixtures.
- No source patches; upstream builds unmodified.

## test_package

- `test_caesiumclt.py` generates a 1x1 PNG from embedded bytes (no network),
  then exercises the packaged binary:
  1. `--version` equals `1.4.0`
  2. `--help` exposes quality/output/compression flags
  3. lossy compress `-q 80 -o <outdir>` produces a non-empty output
  4. `--dry-run` succeeds without writing files
- `conanfile.py` runs the script via `self.run` and emits
  `HMBS_TEST_PACKAGE_RESULT` with `discovered:4/passedCount:4`.

## Verification

Pending HMBS preflight on HarmonyOS aarch64:

```sh
conan create archives/c/caesiumclt/1.4.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

Expected: `cargo build --release --locked` succeeds, `cargo test` 38/38 pass,
package produces `bin/caesiumclt` + `licenses/LICENSE.md`, test_package 4/4 pass.

## Path

Path A (basic adaptation). No Path B/C claim: the Rust fallback pattern is
reused verbatim from cargo-bloat, no new platform knowledge is claimed.
