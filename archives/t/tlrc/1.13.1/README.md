# tlrc — 官方 tldr 客户端（Rust，OHOS PC 适配）

tlrc 是 tldr 官方文档集的 Rust 客户端：在终端里用简洁示例快速查询常用命令用法（如 `tldr tar`）。本目录为 OpenHarmony PC (aarch64) 适配交付物。

## 功能概述

- 查询 tldr 页面仓库中的命令用法（本地缓存 + 自动更新）
- `--render` 本地渲染 markdown 页面（`--raw`/`--compact`/`--short-options` 等）
- `--config` 自定义配色、分页、平台过滤
- 纯 Rust 实现，zip 页面缓存使用 zlib-rs（纯 Rust），TLS 使用 rustls + ring

## OHOS 适配要点

- **Rust 工具链（E180）**：HNP 内置 Rust 1.95+（本机 1.97.1），默认 target 即 `aarch64-unknown-linux-ohos`，直接 `cargo build --release` 即可
- **ring 需要 C 编译器（cc-rs）**：配方内 `env CC=.../aarch64-unknown-linux-ohos-clang cargo build --release`；变量名带连字符不能做 POSIX sh 前缀赋值，须用 `env` 命令传递
- **cargo manifest 搜索**：cargo 会向上搜索 Cargo.toml，配方需 `cwd=source_folder` 并固定 `CARGO_TARGET_DIR`，否则 target 落在非预期目录
- **`.crate` 解压**：crates.io 的 `.crate` 是 gzip tar，conan `get()` 需显式 `filename=xxx.tar.gz` 才能走 tar 分支
- **ELF 签名**：产物 `bin/tldr` 用 `binary-sign-tool sign -selfSign 1` 签名（OHOS 必需，否则 `Operation not permitted`）

## 依赖关系

### 编译依赖
- 无系统 C 库；全部为 cargo crate（clap 4.6.1 / ring 0.17.14 / rustls 0.23.40 / ureq 3.3.0 / zip 8.6.0 等，由 Cargo.lock 锁定）

### 运行依赖
- libc（系统 libc，动态链接 /lib/ld-musl-aarch64.so.1）

## 构建方式

```bash
cargo build --release
# ring crate 需要 C 编译器，需显式传 CC：
env CC=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang cargo build --release
```

产物 `bin/tldr` 为已签名 ELF（2.5MB，stripped）。

## 测试

- 上游自带 cargo 集成测试（`tests/tests.rs`，本地渲染，无网络依赖）：**22/22（100%）通过**（单元 14 + 集成 8，0 failed / 0 skipped）
- test_package 消费者测试：`tldr --version` + `--render` 本地页渲染（2/2，100% 通过）
- conan-verify 门禁 G0-G4 + L2/L4/L5 全部通过

## 参考资料

- 官网：https://tldr.sh/tlrc
- 上游仓库：https://github.com/tldr-pages/tlrc
- 源码（crates.io 官方包）：https://static.crates.io/crates/tlrc/tlrc-1.13.1.crate
- 作者：Lena Pastwa
- 许可证：MIT
