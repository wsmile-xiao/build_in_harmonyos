# spotify_player homebrew 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 预编译二进制方式部署（尝试）
- 编译日期: 2026-06-03
- 编译器: 预编译 musl static ELF (aarch64) — 不可用
- 状态: failed ❌

## 尝试方案与结果

### 方案1: GitHub releases aarch64-unknown-linux-musl 预编译二进制 ❌
- **结果**: GitHub releases 不提供 aarch64-unknown-linux-musl 二进制
- **详情**:
  - v0.23.0 (最新版本): 仅提供 x86_64-unknown-linux-gnu, 无 aarch64 linux
  - v0.22.1 (最新含 aarch64 linux): 提供 aarch64-unknown-linux-gnu (glibc 动态链接, 非 musl)
  - GitHub releases 从未提供过 aarch64-unknown-linux-musl 二进制

### 方案2: aarch64-unknown-linux-gnu 二进制 + patchelf 改 interpreter ❌
- **结果**: 虽然可以通过 patchelf 将 interpreter 改为 /lib/ld-musl-aarch64.so.1, 但运行失败
- **详情**:
  - 二进制类型: "ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-linux-aarch64.so.1)"
  - 原始动态库依赖: libasound.so.2, libdbus-1.so.3, libssl.so.1.0.0, libcrypto.so.1.0.0, libgcc_s.so.1, libpthread.so.0, libm.so.6, libdl.so.2, libc.so.6, ld-linux-aarch64.so.1
  - patchelf 改 interpreter 后: "Error loading shared library libasound.so.2" 等多个库加载失败
  - 还需要大量 glibc/OpenSSL/ALSA/D-Bus 符号: i2d_X509, SSL_read, snd_pcm_writei, dbus_connection_pop_message 等
  - HarmonyOS 系统库: 仅有 /lib/ld-musl-aarch64.so.1, libcrypto.so.3, libssl.so.3, libz.so.1 等 musl 库

### 方案3: cargo-binstall 下载 musl 二进制 ❌
- **结果**: cargo-binstall 无法获取 spotify_player musl 预编译
- **详情**:
  - cargo-binstall 搜索流程: 检查 GitHub releases → 检查 QuickInstall → 回退到 cargo install
  - QuickInstall 无 spotify_player aarch64-unknown-linux-musl 二进制
  - cargo install 回退失败: rustc SIGSEGV (exit 139)

### 方案4: 从源码编译 (cargo build) ❌
- **结果**: rustc 在 HarmonyOS 上 SIGSEGV
- **详情**:
  - rustc --version → exit 139 (SIGSEGV)
  - rustc 是 80KB 薄 wrapper, 动态加载 librustc_driver-545adf06a813b585.so
  - librustc_driver 是 310MB, 需 libgcc_s.so.1 + libc.so
  - libgcc_s.so.1 和 librustc_driver 都安装在 ~/usr/local/lib
  - LD_LIBRARY_PATH 包含 ~/usr/local/lib
  - 但 rustc 仍然崩溃 — 可能是 HarmonyOS kernel/libc 与 rustc 的兼容性问题

### 方案5: Alpine/Chimera APK 包 ❌
- **结果**: spotify_player 不在 Alpine 或 Chimera 的仓库中
- **详情**: Alpine testing 仅有 gst-plugins-rs-spotify (GStreamer 插件, 不是 spotify_player 本身)

### 方案6: pixi 安装 Rust 工具链 ❌
- **结果**: pixi 无法在 HarmonyOS 上创建 conda 环境
- **详情**: pixi init → pixi add rust → "error parsing linux version" (无法解析虚拟包)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 无 musl 二进制 | spotify-player 项目未发布 aarch64-musl 二进制 | 无法解决,需交叉编译 |
| 2 | glibc 二进制不兼容 | 需 glibc dynamic linker + ALSA + D-Bus + OpenSSL 1.0 | HarmonyOS 只有 musl libc |
| 3 | rustc SIGSEGV | rustc/librustc_driver 与 HarmonyOS kernel/libc 不兼容 | 无法在当前环境编译 |
| 4 | cargo-binstall 无 musl 预编译 | QuickInstall 无此 crate | 无法获取 |
| 5 | pixi 无法创建环境 | HarmonyOS 虚拟包解析失败 | 无法通过 pixi 安装 Rust |

## 结论

**spotify_player 当前无法在 HarmonyOS 上部署**。需要以下条件之一才能解决:
1. 上游项目发布 aarch64-unknown-linux-musl 预编译二进制 (最优先)
2. 在其他 Linux 系统上交叉编译 musl static binary (需外部构建环境)
3. 修复 rustc 在 HarmonyOS 上的 SIGSEGV 问题 (需 Rust/HarmonyOS kernel 层面修复)
4. 在 HarmonyOS 上实现 glibc compat layer (复杂, 不推荐)

## 源码修改

无补丁。所有预编译方案均失败。
---

**编译结束**: 2026-06-03 12:50
**最终状态**: failed
