# Helix 25.07.1 Build Notes

## Build Environment
- Target: aarch64-unknown-linux-musl (OpenHarmonyOS)
- Compiler: clang-15 (OHOS SDK)
- Rust: rustc 1.96.0, cargo 1.96.0
- Build system: Cargo (custom)

## Build Steps
1. `cargo build --release` with HELIX_DISABLE_AUTO_GRAMMAR_BUILD=1
2. Manual grammar compilation via shell script
3. Runtime files (grammars + queries) installed alongside hx binary

## Issues Encountered
- Grammar compilation: 242/245 failed initially due to missing CRT objects and libraries (ld.lld couldn't find crti.o, crtbeginS.o, crtendS.o, crtn.o, -lstdc++, -lgcc_s, -lgcc)
- Solution: Build grammars manually using shell script with proper compiler flags (--sysroot, -fuse-ld=lld)
- GitHub unreachable: couldn't fetch grammar sources (already present in source tarball)
- rustdoc permission error during cargo test doctests

## Modified Files
- helix-term/build.rs: Skip fetch_grammars() (GitHub unreachable), only call build_grammars()
- helix-loader/src/grammar.rs: Add OHOS sysroot/include/lib paths for grammar C/C++ compilation
---

**编译结束**: 2026-06-16 01:15
**最终状态**: built
