# cargo-bloat 0.12.1 Path B evidence

## Claim boundary

This adaptation claims Path A for the package recipe and Path B for the
reusable HarmonyOS Rust toolchain knowledge. It does not claim that the
upstream cargo-bloat source is intrinsically complex, and it does not claim
Path C or complete upstream test coverage.

Upstream is a pure Rust Cargo subcommand with one executable, no Conan
dependencies, no source patches, and no Rust test suite. Its GitHub workflow
only runs `cargo build` with and without default features. The Path B value is
the isolated toolchain and device-execution solution required to build and
exercise that executable on the HarmonyOS aarch64 runner.

## Reusable HarmonyOS findings

The base device image exposes Conan and the OHOS compiler but no `cargo` or
`rustc`. The recipe therefore downloads four arm64 OHOS Harmonybrew bottles
into the Conan build folder only:

- Rust 1.97.1
- OpenSSL 3.6.3
- zlib-ng compatibility runtime
- CA certificates

Every archive is SHA256 verified before extraction. The fallback is enabled
only for OHOS, does not install into the device image or user home, and keeps
Cargo/Rust environment changes inside the Conan build and test processes.

The investigation produced four reusable findings:

1. Harmonybrew Rust wrappers can contain hard-coded Cellar paths. A relocated
   bottle must discover the actual `cargo.real` and either `rustc.real` or
   `rustc`, then repair local wrappers before use.
2. `cargo.real` needs the OpenSSL and zlib bottle library directories in
   `LD_LIBRARY_PATH`; locating the executable alone is insufficient.
3. Passing Conan's generated `conanrun` environment to `self.run()` can replace
   the fallback Cargo path. A recipe that provisions tools dynamically must
   compose and restore its process environment explicitly.
4. The device execution policy rejects a wrapper or ELF reached through the
   test source directory, and a symlink does not change that decision. Copying
   `cargo.real` into the runner-owned `TMPDIR`, setting mode `0750`, and
   prepending that directory to `PATH` provides an executable shim without
   mutating the device image. The test removes this shim directory on exit.

## Failure evolution and root causes

| Runner stage | Result | Root cause and correction |
| --- | --- | --- |
| preflight | blocked | `cargo` and `rustc` were absent; added the checksum-pinned OHOS-only fallback. |
| create r1 | failed | The Rust bottle contains `rustc` rather than only `rustc.real`; tool discovery now accepts both layouts. |
| create r2 | package passed, test failed | `env="conanrun"` replaced the fallback Cargo path; test execution now preserves the composed environment. |
| create r3 | test failed | Direct `cargo.real` lacked OpenSSL/zlib runtime libraries; bottle library directories are now injected. |
| create r4 | test failed | The device rejected execution from the test source directory; an executable runner-temp shim was introduced. |
| create r5 | test failed | A symlink still resolved to the denied source path; the shim now copies the real executable. |
| create r6 | passed | The copied runner-temp Cargo shim and explicit runtime environment passed version, help, fixture build, and ELF analysis. |

## Reproduction

The final single-package command was:

```sh
conan create archives/c/cargo-bloat/0.12.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Runner task: `cargo-bloat-0.12.1-create-r6-20260820`.

Observed final result:

```text
exit_code=0
cargo-bloat version/help/ELF analysis checks passed
```

The package build produced `bin/cargo-bloat` and `licenses/LICENSE`. The test
package verified `cargo-bloat bloat --version`, `--help`, and a
dependency-free Cargo fixture analyzed through `--crates`, regex filtering,
and JSON output.

## Evidence boundary

- The package build completed during the r2 investigation; r6 reused that
  Conan package revision and reran the final test package successfully.
- No upstream tests were removed or rewritten because version 0.12.1 contains
  no Rust `#[test]` cases and its upstream CI is build-only.
- The repository-wide L0 R38 gate requires software-level CLI metadata. The PR
  therefore includes `archives/c/cargo-bloat/commands.json` with `type: tool`,
  version `0.12.1`, and `binary: true`; no CI infrastructure is changed.

## Path B contribution

The reusable contribution is a checksum-pinned, relocatable Rust/Cargo
fallback plus a verified workaround for HarmonyOS runner execution policy.
The same pattern applies to other Rust CLI recipes when the target worker has
an OHOS compiler and Conan but no preinstalled Rust toolchain. The recipe also
documents the security boundary: TLS verification is preferred, the fixed
mirror fallback remains SHA256 pinned, archive extraction rejects path
traversal, and no global installation is performed.

## CI follow-up

AtomGit CI build `#28865` confirmed that the R38 metadata and knowledge checks
passed. Its next failure exposed a separate worker-environment case: a
preinstalled `cargo.real` bypassed the fallback bootstrap, so the previous
bootstrap-only CA setup never reached Cargo. The recipe now applies the CA
bundle to both preinstalled and fallback toolchains through Cargo `cainfo`,
`CARGO_HTTP_CAINFO`, `SSL_CERT_FILE`, and `CURL_CA_BUNDLE`; if no system bundle
exists, it extracts the checksum-pinned CA bottle in the isolated build folder.
