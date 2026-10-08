# Adaptation Notes — lss 1.0

## Software Info
- Name: lss (Linux Syscall Support)
- Version: 1.0
- Type: Header-only library
- Main file: linux_syscall_support.h
- Upstream: https://chromium.googlesource.com/linux-syscall-support

## Adaptation Steps
1. Source downloaded from GitHub mirror (getsentry/linux-syscall-support) because googlesource.com not accessible
2. Patch 0001-loff_t-compat.patch: adds `typedef long long loff_t;` for musl libc compatibility
3. conanfile.py: header-library package type, no build step
4. test_package: includes and calls sys_getpid() and sys_close() (R34 compliant)

## Build Issues
- loff_t not defined in OHOS musl libc → fixed by patch
- conan copy() function not working on OHOS → using shutil.copy2 directly

## Verification
- conan-verify: PASS (G1, G2, G3, G4, L2, L4, L5)
- W3 local CI: PASS
- test_package: PASS (sys_getpid returns positive PID, sys_close(-1) returns -1)
---

**编译结束**: 2026-09-18 16:38
**最终状态**: published
