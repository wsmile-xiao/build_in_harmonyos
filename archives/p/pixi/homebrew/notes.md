# pixi homebrew 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 预编译 musl 二进制方式部署
- 编译日期: 2026-06-03
- 编译器: 预编译 musl static ELF (aarch64)
- 状态: built

## 编译步骤

### 第1次尝试（成功 — GitHub static binary + ELF签名）
1. 下载 GitHub Release 预编译 pixi-aarch64-unknown-linux-musl (v0.70.0)
   - URL: https://github.com/prefix-dev/pixi/releases/download/v0.70.0/pixi-aarch64-unknown-linux-musl
   - 提取的 binary: "ELF executable, 64-bit LSB arm64, static, stripped" (~61MB)
2. ELF签名: binary-sign-tool sign -selfSign 1 -inFile pixi-gh -outFile pixi-signed -signAlg SHA256withECDSA
3. 运行验证: pixi-signed --version → "pixi 0.70.0" (exit 0) ✅

### 关键发现
- pixi的static musl binary在HarmonyOS上可以正常运行(不像xh/duf等会SIGSEGV)
- Alpine/Chimera Linux均无pixi包可用
- GitHub static binary约61MB (pixi是大型Rust项目，包含conda求解器等)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build SSL证书验证失败 | 环境SSL证书不全 | 手动下载源码tarball，手动创建归档骨架 |
| 2 | GitHub直连超时 | 网络限制 | 使用ghfast.top代理下载 |
| 3 | pixi不在Alpine/Chimera repos | 新软件，尚未被Alpine/Chimera收录 | 使用GitHub release static binary |

## 源码修改

无补丁。使用预编译二进制方式部署。
---

**编译结束**: 2026-06-03 11:57
**最终状态**: built
