# cargo-binstall — Rust Binary Installer

## Description
cargo-binstall is a tool to install Rust binaries from their release assets on GitHub or other sources, without needing to compile from source. It provides a fast way to install pre-built Rust tools.

## Dependencies
- No compilation dependencies (precompiled binary approach)
- Runtime: musl libc (system provided via /lib/ld-musl-aarch64.so.1)

## HarmonyOS Adaptation Notes
- **Precompiled approach**: rustc crashes (SIGSEGV) on HarmonyOS, so we use precompiled binaries from GitHub releases
- **Static musl binary works**: Despite initial concerns, the aarch64-unknown-linux-musl static binary works on HarmonyOS Kernel 1.12.0
- **Three binaries required**: cargo-binstall, detect-targets, detect-wasi must all be installed together
- **ELF signing**: All binaries require adhoc self-sign via binary-sign-tool

## Versions
| Version | Status | Date |
|---------|--------|------|
| homebrew (v1.19.1) | ✅ published | 2026-06-03 |