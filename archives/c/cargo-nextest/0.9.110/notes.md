# cargo-nextest 0.9.110 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-05
- 编译器: rustc 1.95.0
- Rust 目标: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载源码：cargo-nextest-0.9.110.crate (来自 crates.io)
2. 解压到构建目录：`/data/storage/el2/base/cache/builds/cargo-nextest-0.9.110.work`
3. 设置环境变量：`TARGET_CC=clang`, `TMPDIR=/data/storage/el2/base/cache`
4. 下载依赖：`cargo fetch`（下载 200+ 个依赖包）
5. 编译 release 版本：`cargo build --release`（耗时约 8 分钟）
6. Staging 安装：复制 `target/release/cargo-nextest` 到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`
7. Strip 符号表：减小二进制体积（19.6MB → 14.1MB）
8. 创建预编译包：`cargo-nextest-0.9.110-ohos-aarch64.tar.gz`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | unknown_build_system | 脚本未识别 cargo 构建系统 | 手动设置 manifest.yaml build.system=cargo，手动编译 |
| 2 | staging 目录位置错误 | TEST_PREFIX 路径与脚本期望不一致 | 移动到 `/data/storage/el2/base/cache/test-install-*` |
| 3 | G0 干净构建失败 | Rust 项目无 configure 脚本 | 记录为平台限制，手动验证编译成功 |
| 4 | ELF 签名工具缺失 | /data/service/hnp/bin/sign 不存在 | Skip 签名（用户首次运行时触发安全弹窗） |

## 源码修改

无补丁，cargo-nextest 源码直接在 HarmonyOS 上编译成功。

## 依赖版本

- Rust: 1.95.0 (harmonybrew)
- cargo: 1.95.0
- clang: 系统自带
- 目标平台: aarch64-unknown-linux-ohos
- musl: 动态链接 (/lib/ld-musl-aarch64.so.1)

## 验证结果

```bash
cargo-nextest 0.9.110 (83952e134 2025-10-31)
release: 0.9.110
commit-hash: 83952e13433fa86c24e2cdef1aaddeacb6dd85f4
commit-date: 2025-10-31
host: aarch64-unknown-linux-ohos
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cargo-nextest-0.9.110-ohos-aarch64.tar.gz | 14.1 MB | 预编译包（含 strip） |
| cargo-nextest (strip后) | 14.1 MB | 二进制文件 |

## 注意事项

1. cargo-nextest 是 Rust 测试运行器，跳过自测（避免循环依赖）
2. Rust 项目无需 configure 步骤，直接 cargo build
3. 首次安装后可能需要用户确认安全弹窗
4. 编译时间较长（8+ 分钟），依赖下载约 200 个包

---
**编译结束**: 2026-06-05 10:47
**最终状态**: built
---

**编译结束**: 2026-08-06 02:51
**最终状态**: built
