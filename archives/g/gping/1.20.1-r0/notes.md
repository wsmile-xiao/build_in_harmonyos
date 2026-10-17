# gping 1.20.1-r0 编译笔记

## 编译信息
- **软件**: gping (Ping with a graph)
- **版本**: 1.20.1-r0
- **编译系统**: Cargo (Rust)
- **编译日期**: 2026-06-04
- **状态**: ✅ PUBLISHED

## 编译过程记录

### Phase 0: 环境准备
- 设置 TMPDIR=/data/storage/el2/base/cache ✅
- 检查 Rust 工具链 ✅ (harmonybrew rustc 1.95.0, cargo 1.95.0)

### Phase 1: 工具链获取
- usr/local/bin 下的 rustc/cargo 二进制损坏（ELF header section 21-22 sh_type 为 SHT_NULL）
- 使用 harmonybrew 安装的 Rust 工具链 (rustc 1.95.0, cargo 1.95.0) ✅
- cargo-binstall 通过 cmd-pkgs 安装 ✅

### Phase 2: 源码获取与编译
- 下载 gping 源码 (GitHub codeload) ✅
- cargo build --release 成功 (耗时约 2 分钟)
- 依赖下载使用 rsproxy-sparse 中国镜像 ✅

### Phase 3: 安装与验证
- 安装到 DESTDIR staging area ✅ (R20 DESTDIR模式)
- 安装到 DEFAULT_PREFIX (~/usr/local) ✅
- RPATH 修复：/storage/Users/currentUser/.harmonybrew/lib:/storage/Users/currentUser/usr/local/lib ✅
- ELF 签名 (binary-sign-tool self-sign) ✅
- gping --version 验证通过 ✅

## 验证结果

```bash
$ ~/usr/local/bin/gping --version
gping 1.20.1
commit_hash: 
build_time: 2026-06-04 16:14:57 +08:00
build_env: rustc 1.95.0 (59807616e 2026-04-14),
```

## 源码修改
无（无补丁，使用原始源码编译）

## 依赖版本

**构建依赖**：
- Rust 编译器 (rustc) 1.95.0 — via harmonybrew
- Cargo 1.95.0 — via harmonybrew
- libssl.so.3 (OpenSSL 3.6.2) — via harmonybrew
- libgcc_s.so.1 — via harmonybrew

**系统已有**：
- clang 15.0.4 (DevBox)
- cmake 4.1.2
- make 4.4.1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | usr/local/bin 下的 rustc/cargo 无法运行 | ELF header 损坏 (section 21-22 sh_type SHT_NULL, 应为 SHT_STRTAB) | 使用 harmonybrew 安装的 Rust 工具链 |
| 2 | cargo 无法找到 libssl.so.3/libgcc_s.so.1 | HarmonyOS musl namespace 系统不允许 RUNPATH 加载用户目录的共享库 | harmonybrew 的 cargo/rustc 有正确的 RUNPATH 指向 harmonybrew 目录 |
| 3 | Python 3.14 ssl 模块无法加载 | libssl 在 namespace 中无法被找到 | Python RUNPATH 包含 harmonybrew/opt/openssl@3/lib |
| 4 | init-build 下载超时 | GitHub SSL 证书问题 + 网络限制 | 手动下载 + codeload.github.com |
| 5 | cargo config TOML duplicate key | 之前写入的 config.toml 包含重复的 [source.crates-io] | harmonybrew 自动生成了正确的 config |

## 知识提取记录

### E-001: Rust 工具链在 HarmonyOS 上的适配
- **问题**: 预安装的 cargo/rustc 二进制有损坏的 ELF headers
- **影响**: 所有依赖 cargo/rustc 的 Rust 项目无法编译
- **证据**: section 21-22 的 sh_type 为 SHT_NULL (应为 SHT_STRTAB)
- **解决方案**: 使用 harmonybrew 安装的 Rust 工具链 (有正确的 RUNPATH 和 ELF 结构)

### E-002: HarmonyOS musl namespace 限制
- **问题**: 动态链接器不加载 RUNPATH 指向的用户目录中的共享库
- **影响**: 用户安装的二进制无法找到 libssl.so/libgcc_s.so 等
- **证据**: Error relocating ... symbol not found (libssl, libcrypto, libgcc)
- **解决方案**: harmonybrew 的二进制有 $ORIGIN/../lib RPATH，可以被 musl linker 找到

---
**编译结束**: 2026-06-04 16:16
**最终状态**: published
---

**编译结束**: 2026-08-06 16:00
**最终状态**: built

