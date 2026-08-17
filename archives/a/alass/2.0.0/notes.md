# alass 2.0.0 HarmonyOS PC adaptation notes

## Scope and status

- Issue: 2224
- Branch: `feat/alass-2.0.0-2224`
- Build system: Cargo workspace (Rust 2018)
- Status: built and tested successfully with single-package HarmonyOS shadow CI
- Adaptation path: Path A + Path B knowledge-extension candidate
- Source patch: `0001-update-rust-runtime-dependencies.patch`

## W0 dependency check

`alass` has no Conan library dependencies. The source lock file contains no Git dependencies. The `webrtc-vad` crate builds bundled C code with the compiler selected by Conan.

FFmpeg and ffprobe are optional runtime dependencies only when a video file is the reference. Subtitle-to-subtitle synchronization does not need them, so issue 2224 does not mix in an FFmpeg adaptation.

Build prerequisites are Rust/Cargo and clang. They are runner toolchain requirements, not libraries to publish in this PR.

Official CI workers do not uniformly provision Rust/Cargo. When an OHOS worker
has no usable toolchain, the recipe uses Conan `get()` to bootstrap the official
Harmonybrew Rust 1.97.1, OpenSSL 3.6.3, zlib, and CA certificate bottles. All
four arm64_ohos bottle SHA-256 values are pinned from the official Harmonybrew
formulas; the fallback does not skip the build or any upstream test.

## Source and build analysis

- Official tag: `v2.0.0`
- Source: `https://github.com/kaegi/alass/archive/refs/tags/v2.0.0.tar.gz`
- SHA-256: `ce88f92c7a427b623edcabb1b64e80be70cca2777f3da4b96702820a6cdf1e26`
- Workspace members: `alass-core`, `alass-cli`
- Output: `target/release/alass-cli`
- C-backed crate: `webrtc-vad 0.4.0`

The recipe reads `CC` and `CXX` from Conan's `tools.build:compiler_executables`, passes the Conan C compiler to Rust as the linker, and keeps Cargo and temporary outputs in writable build-local directories.

The original lock graph (`ctrlc 3.1.3`, `nix 0.14.1`, and `libc 0.2.62`) is incompatible with Rust 1.97 for `target_env=ohos`. The portability patch updates these dependencies and deterministic transitive lock entries within upstream semver constraints. The main recipe and `test_package` export identical patch content. `CARGO_BUILD_JOBS=1` avoids intermittent `Text file busy (os error 26)` failures seen during parallel build-script execution on the device.

## Tests

The three active upstream tests are:

1. `alass-core/src/alass.rs::tests::run_aligner`
2. `alass-core/src/alass.rs::tests::test_single_span_ratings`
3. `alass-core/src/timespan_ops.rs::tests::test_prepare_time_spans`

They run with:

```sh
cargo test --workspace --release --locked --tests
```

The consumer test invokes the packaged executable and checks five behaviors: version, help, a real one-second subtitle correction, corrected timestamp, and preserved subtitle text. This exercises parsing, alignment, correction, and serialization without FFmpeg.

## Local validation

- Official archive download, SHA-256, and extraction: PASS
- Python AST for both recipes: PASS
- YAML parsing and invariants: PASS
- Conan inspect, export, and source method: PASS
- Project review: 12 PASS, 1 expected warning, 0 FAIL

## HarmonyOS shadow CI

- Run ID: `codex-unknown-lib-alass-2.0.0-2224-r8-20260816-150649-14297`
- Time: 2026-08-16 15:06:50 to 15:16:54 +0800
- Profile: `ohos-aarch64`
- Toolchain: Conan 2.31.2, Cargo 1.97.1, rustc 1.97.1, clang 15.0.4
- Main build and package: PASS; package contains `bin/alass-cli` and `LICENSE`
- Main upstream suite: PASS, 3/3
- Consumer smoke: PASS, 5/5
- Fresh-source upstream suite in `test_package`: PASS, 3/3
- Destructive negative test: PASS
- Gates: L0, L1, L2, L4, and L5 PASS
- Runner stderr: empty
- Device lock: released after completion

L0k emitted a non-blocking warning because CLI metadata belongs at software level (`archives/a/alass/commands.json`), outside this version-only change scope. Rust reported upstream `nom 2.1.0` as future-incompatible, but it passed with Rust 1.97.1. A transient package-cache network warning recovered automatically.

Official AtomGit CI additionally exposed two worker-image gaps: some workers use
a Conan Python without the SSL module, and the source-capable workers do not have
Rust/Cargo installed. The former is a platform-level transient condition handled
by retrying another worker. The latter is handled in-recipe with the same
Harmonybrew OHOS bottle bootstrap already used by the merged `argc/1.24.0`
adaptation, strengthened here with Conan-native downloads and official bottle
SHA-256 verification.
CI #26172 then completed the bootstrap, release build, 3/3 main-recipe upstream
tests, packaging, and 5/5 consumer tests. Its only failure was the independent
fresh-source test timing out against GitHub. The fresh-source download now uses
the CI-accessible `gh-proxy` mirror first with the official archive as fallback;
both are verified against the same pinned source SHA-256.

## Path B knowledge-extension candidate

The Path B application is limited to one reusable contribution: a deterministic procedure for migrating a legacy Rust Unix dependency lock graph when old `ctrlc`, `nix`, and `libc` releases do not support the modern Rust/OHOS `target_env=ohos` combination.

Evidence is recorded in `reports/path-b-candidate.md` and `knowledge/drafts/E327-draft-1945.{kv,md}`. The method preserves upstream manifest constraints, updates the smallest direct root dependency within semver bounds, exports the resulting lock-file delta as a source patch, and keeps `--locked` for both build and tests. It explicitly forbids unbounded `cargo update`, removing `--locked`, or modifying the shared Cargo registry cache.

The application does not claim the following as new knowledge:

- choosing Harmonybrew `.real` Cargo/rustc siblings, which has an existing `argc` precedent;
- using one Cargo job for ETXTBSY, which has an existing `librsvg` precedent;
- ordinary Conan recipe and consumer-test construction, which belongs to Path A.

This is submitted as a Path B candidate rather than a self-assigned result. It does not claim Path C: alass has no private OS API, assembly, JIT, cross-architecture runtime, large mandatory Conan dependency graph, or multi-process system test surface.

## Reproduction

```sh
CI_PACKAGES="archives/a/alass/2.0.0" zsh ci/conan/build_and_test.sh
```

For a direct isolated diagnostic:

```sh
conan create archives/a/alass/2.0.0 \
  -pr:h="$CONAN_HOME/profiles/ohos" \
  -pr:b="$CONAN_HOME/profiles/ohos" \
  --build=missing
```

Let the runner assign `RUN_DIR` and use task-local `HOME`, `CONAN_HOME`, `CARGO_HOME`, `TMPDIR`, and `TMPPREFIX`. When Harmonybrew wrappers are not executable, use their `.real` Cargo/rustc siblings.

## Final status

status: closed
COMPLETED: alass 2.0.0 passed single-package HarmonyOS shadow CI.
