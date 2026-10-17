# Stalwart CLI 1.0.5 adaptation notes

## Source

- Upstream: `stalwartlabs/cli`
- Tag: `v1.0.5`
- Commit: `ca7b5d73a57b587f3aa04b2ecd3a4c6491314585`
- The task-board name `stalwart` maps to the upstream `stalwart-cli` binary.

## Build adaptation

The native Rust toolchain reports host and target
`aarch64-unknown-linux-ohos`. Cargo is configured with the Conan profile's C
compiler as linker; no Linux binary or alternate Rust target is substituted.
The recipe checks Cargo candidates from `PATH`, `CARGO_HOME`, and the official
installer locations `$HOME/.cargo/bin/cargo` and
`$HOME/usr/rust-1.95.0-aarch64-unknown-linux-ohos/bin/cargo`. Each candidate is
accepted only when it forms an executable cargo/rustc pair, reports Cargo and
rustc 1.95.0, and reports rustc host `aarch64-unknown-linux-ohos`. If no valid
pair exists, the recipe downloads the official OpenHarmonyPCDeveloper Rust
1.95.0 release archive, verifies SHA256, extracts it under `self.build_folder`,
and validates that pair with the same checks. No global toolchain directory is
modified. This is required because CI workers may omit Rust entirely, while
PATH may also contain an unrelated Linux toolchain. The selected toolchain
directory is prepended only to the Conan build environment. `HOME` and
`CARGO_HOME` are also set to build-local directories so user Cargo config,
credentials and caches cannot alter registry, linker or target behavior.
Cargo's HTTPS client receives the CA bundle already used by Conan's Python
runtime through `CARGO_HTTP_CAINFO`; this avoids depending on a Worker-specific
system CA location without disabling TLS verification. Build/test commands
explicitly pass `--target aarch64-unknown-linux-ohos`.

`reqwest 0.13.2` selects rustls and `aws-lc-sys 0.39.1`. That crate already
contains an OHOS CMake path: with the SDK toolchain and a clean Cargo target
directory it selects the official `linux-aarch64` assembly source set while
Cargo, rustc, clang and the final executable remain targeted at OHOS.

The current SDK contains `native/llvm/bin/llvm-ar` but no sibling
`native/llvm/bin/llvm-ranlib`; its CMake toolchain nevertheless records the
missing path and AWS-LC fails while indexing its static archive. The recipe
creates a build-local wrapper that invokes `llvm-ar s`, then supplies a thin,
target-specific CMake toolchain overlay through aws-lc-sys's documented
`AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos` hook. No SDK or
Cargo registry file is modified.

## Consumer verification

`test_package` executes the packaged binary and uses a localhost-only random
port mock JMAP service. It verifies exact version output, help commands, Basic
authentication, schema retrieval, session retrieval, object rendering and the
401 authentication error path. No public network service or production secret
is used by the consumer test.

## Upstream tests

The source contains 75 unit tests and 13 integration tests (88 discovered).
`cargo test --release --locked --target aarch64-unknown-linux-ohos -- --nocapture`
executed and passed all 75 unit tests. All
13 integration test functions returned early after printing that the Stalwart
server at localhost:8080 was unreachable. Cargo reports those functions as
`ok`, but this archive conservatively records them as skipped rather than
passed because their protocol assertions did not execute.
---

**编译结束**: 2026-08-17 02:41
**最终状态**: built
