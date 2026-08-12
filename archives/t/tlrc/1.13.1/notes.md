# tlrc 1.13.1 适配笔记

## 编译环境
- 构建系统: cargo（Rust 1.97.1，target aarch64-unknown-linux-ohos）
- 编译日期: 2026-08-09
- 编译器: rustc 1.97.1 + clang 15.0.4（ring crate 的 cc-rs 需要）
- 状态: published

## 编译步骤

```bash
# 源码：crates.io 官方 .crate 包（SHA256 与 crates.io API checksum 一致）
# 下载并解压后直接：
cargo build --release
# 说明：~/.cargo/config.toml 已配置
#   [target.aarch64-unknown-linux-ohos]
#   linker = "aarch64-unknown-linux-ohos-clang"
#   rustflags = ["-C", "link-arg=-fuse-ld=lld"]
# ring crate 需要 C 编译器，构建时需显式传 CC：
env CC_aarch64-unknown-linux-ohos=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    CC_aarch64_unknown_linux_ohos=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    CC=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
    cargo build --release
```

产物：`target/release/tldr`（ELF arm64，动态链接 /lib/ld-musl-aarch64.so.1，stripped，2.5MB）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan get()` 报 `BadZipFile: File is not a zip file` | `.crate` 是 gzip tar，conan 按扩展名识别解压方式 | source() 显式传 `filename="tlrc-1.13.1.tar.gz"` 走 tar 分支 |
| 2 | ring 编译报 `failed to find tool "cc"` | cc-rs 需要 C 编译器，conan 环境未设置 CC | build() 内联 `env CC=.../aarch64-unknown-linux-ohos-clang cargo build --release` |
| 3 | `/bin/sh: CC_aarch64-unknown-linux-ohos=...: inaccessible` | 变量名带连字符不能做 POSIX sh 前缀赋值 | 改用 `env VAR=... cmd` 形式传环境变量 |
| 4 | package() 找不到 `target/release/tldr` | cargo 会向上搜索 Cargo.toml，target 落在 build 目录的父级 | build() 指定 `cwd=source_folder` 并固定 `CARGO_TARGET_DIR=build_folder/target` |
| 5 | （预期）test_package 运行二进制报 Operation not permitted | OHOS ELF 未签名 | package() 内用 `binary-sign-tool sign -selfSign 1` 签名（先 llvm-objcopy 移除 .codesign） |

## 源码修改

无（零源码修改，纯 cargo 构建即可，无补丁）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| clap | 4.6.1 | CLI 解析（derive） |
| ring | 0.17.14 | TLS 加密（cc-rs 需要 C 编译器） |
| rustls | 0.23.40 | TLS（ring provider） |
| ureq | 3.3.0 | HTTP 客户端（rustls-no-provider + platform-verifier） |
| zip | 8.6.0 | tldr 页面 zip 缓存（deflate-flate2-zlib-rs，纯 Rust） |
| toml / serde / yansi 等 | - | 纯 Rust crate |

全部依赖为 cargo crate（crates.io），无系统 C 库依赖。

## 验证结果

```bash
$ ./target/release/tldr --version
tlrc v1.13.1 (implementing the tldr client specification v2.3)

$ cargo test --release
# 单元测试：14 passed; 0 failed
# 集成测试 tests/tests.rs：8 passed; 0 failed
# 总计 22/22（100%）

$ python3 scripts/ohc-run.py conan-verify tlrc 1.13.1
✅ 配方验证通过: tlrc 1.13.1（G0-G4 + L2/L4/L5 全 PASS）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/tlrc-1.13.1-ohos-aarch64.tar.gz | - | 产物包（bin/tldr，已签名） |
| reports/test-report.md | - | 功能测试报告 |
| reports/conan-verify-report.md | - | conan-verify 门禁报告 |
| reports/conan-create.log | - | conan create 构建日志 |
| conanfile.py + conandata.yml | - | Conan 配方 |
| test_package/ | - | 消费者视角测试（含 MANIFEST.yml） |

## 注意事项

- tlrc 是官方 tldr 客户端（Rust），网络功能（下载 tldr 页面）需要联网，test_package 仅做 `--version` 与本地 `--render` 冒烟验证。
- 上游自带 cargo 集成测试（tests/tests.rs，本地渲染无网络依赖），已在本地全量执行 22/22 通过。
- Rust 工具链依赖 HNP 内置 Rust 1.95+（E180 rust-native-compile，本机 1.97.1），默认 target 即 aarch64-unknown-linux-ohos。
- 分支名：`feat/tlrc-1.13.1`；PR 前缀：【积分赛】。

## 结束标记
最终状态: published
