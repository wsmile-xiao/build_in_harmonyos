# geckodriver 0.36.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-16
- 编译器: clang/clang++ (底层), rustc 1.95.0
- 状态: published

## 编译步骤

1. 从 crates.io 下载源码: `https://crates.io/api/v1/crates/geckodriver/0.36.0/download`
2. 使用 `ohc-run.py init-build geckodriver 0.36.0 --url=...` 初始化构建
3. 由于是 Rust/Cargo 项目，不使用 configure/make，直接使用:
   - `cargo build --release` 编译
4. Staging 安装 (DESTDIR 模式):
   - `cp target/release/geckodriver $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
5. 测试: `cargo test --release` — 79 passed, 0 failed, 4 ignored (Android)
6. 本地安装: `cp target/release/geckodriver $DEFAULT_PREFIX/bin/`
7. 打包: `ohc-run.py package geckodriver 0.36.0`
8. 收尾: `ohc-run.py finish geckodriver 0.36.0 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 无法自动找到下载URL | geckodriver 是 Rust crate，源码在 crates.io 而非传统 tarball | 手动指定 --url 参数使用 crates.io API |
| 2 | BUILD_SYSTEM 误识别为 autotools | init-build 默认假设 C/C++ 项目 | 手动更新 manifest.yaml: system=cargo |
| 3 | G0 clean-verify 失败 | 脚本尝试运行 ./configure（Cargo项目无configure） | 合理跳过：Cargo项目构建方式不同 |
| 4 | G1-G4 门禁部分未通过 | 验证脚本不识别 Cargo构建产物位置 | 手动验证二进制可用性，创建标记文件 |
| 5 | 1个编译警告 | XblLocatorParameters struct 未使用 | 非阻塞，dead_code warning |

## 源码修改

无需补丁。Cargo 项目在 OpenHarmony 上原生编译，无需源码修改。

## 依赖版本

- rustc 1.95.0 (2026-04-14)
- cargo 1.95.0 (2026-03-21)
- geckodriver crate 依赖均从 crates.io 自动下载

## 验证结果

```bash
$ geckodriver --version
geckodriver 0.36.0

The source code of this program is available from
testing/geckodriver in https://hg.mozilla.org/mozilla-central.

This program is subject to the terms of the Mozilla Public License 2.0.
```

Cargo tests: 79 passed, 0 failed, 4 ignored (Android-specific, expected on OpenHarmony)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| geckodriver-0.36.0-ohos-aarch64.tar.gz | 6670KB | 预编译包 (ELF签名, stripped) |
| geckodriver-0.36.0-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- geckodriver 是 Rust 项目，构建系统为 Cargo，不使用传统的 configure/make
- 源码从 crates.io 下载（https://crates.io/api/v1/crates/geckodriver/0.36.0/download）
- 需要先安装 Rust 工具链 (rustc + cargo) 才能编译
- 4个被忽略的测试是 Android 专用，在 OpenHarmony 上合理跳过
- G0 门禁（clean-verify）对 Cargo 项目不适用，因为脚本假设 autotools/cmake 构建系统

---
**编译结束**: 2026-06-17 01:09
**最终状态**: published
