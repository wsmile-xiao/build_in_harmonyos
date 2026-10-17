# aribb24 1.0.3 — Adaptation Notes

## Software
- Name: aribb24
- Version: 1.0.3
- Upstream: https://github.com/nkoriyama/aribb24
- Build system: autotools (configure.ac + Makefile.am + libtool)
- Dependencies: libpng/1.6.58

## Build Steps
1. autoreconf -fi (pre-generated, included in generated/)
2. ./configure --prefix=$DEFAULT_PREFIX --disable-shared --enable-static
3. make -j1
4. make install (manual copy in package())

## Patches
- Makefile.am: Add $(PNG_CFLAGS) to libaribb24_la_CFLAGS for proper png header detection

## HarmonyOS Platform Issues & Fixes

### E165: HMDFS symlinks cannot be executed through shebangs
- Fix: Replace `#!/bin/sh` with `#!/system/bin/sh` in configure and libtool scripts
- Fix: Run configure through `bash` instead of direct execution

### E046: HMDFS chmod does not work
- Fix: Run configure through bash (bypasses file exec permission check)

### config.status umask 077 creates inaccessible temp dirs
- Fix: Replace `umask 077` with `umask 022` in config.status

### libtool tool paths use inaccessible HMDFS symlinks
- Fix: Replace SED, GREP, EGREP, FGREP paths with accessible alternatives

### clang-15 从 Python subprocess 执行失败 — 根因：stdin socket
- 根因：OpenDesk executeZsh 工具的 zsh 进程 stdin 是 Unix socket，Python 继承后，clang-15 初始化时对 stdin 调用 fstat() 返回 EACCES，导致静默退出 rc=1
- 修复：在 sitecustomize.py 中为 subprocess.run 默认设置 stdin=DEVNULL（基础设施层面统一修复，无需逐包修改）
- CI 环境不受影响（CI 的 stdin 不是 Unix socket）
- 其他二进制（llvm-ar 等）不受影响，因为它们初始化时不调用 fstat(stdin)

## Status
- built (conan-verify all gates passed: G1/G0/G2/G3/G4/L2/L4/L5)
---

**编译结束**: 2026-08-12 17:31
**最终状态**: built
