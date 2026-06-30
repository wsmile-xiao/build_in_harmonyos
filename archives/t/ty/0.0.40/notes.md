# ty 0.0.40 — Build Notes

## Overview
- **Software**: ty (typos spell checker)
- **Version**: 0.0.40
- **Build Method**: Prebuilt binary (upstream binary for aarch64-unknown-linux-gnu)
- **Reason for prebuilt**: rustc crashes with SIGSEGV on local HarmonyOS environment

## Build Process
1. Downloaded upstream prebuilt binary from ty-aarch64-unknown-linux-gnu release
2. ELF-signed with binary-sign-tool (--selfSign 1)
3. Verified codesign section with llvm-readelf
4. Stripped symbols with llvm-strip
5. Packaged using DESTDIR staging mode

## Issues
- rustc SIGSEGV prevents local compilation
- Used upstream prebuilt binary as workaround
---

**编译结束**: 2026-06-02 11:46
**最终状态**: built
