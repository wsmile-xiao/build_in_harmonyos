# tinymist 0.12.2 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-08
- 编译器: clang/clang++ (system), cargo 1.95.0 (rustc)
- 状态: published

## 编译步骤

1. 下载源码: ghfast.top 镜像 (SSL证书问题导致自动下载失败，手动用 curl -kL 下载)
2. init-build: ohc-run.py init-build tinymist 0.12.2 --no-download
3. 编译: cd $BUILD_SRC_DIR; cargo build --release -p tinymist
4. 安装到staging: cp target/release/tinymist $TEST_PREFIX/$DEFAULT_PREFIX/bin/
5. 安装到本地: cp target/release/tinymist $DEFAULT_PREFIX/bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败导致自动下载失败 | 平台SSL证书链不完整 | 使用 curl -kL 手动下载并 --no-download 初始化 |

## 依赖版本

- Rust/cargo 1.95.0
- clang 15.0.4 (系统编译器)

## 验证结果

```bash
$ tinymist --version
tinymist
Build Timestamp:     2026-06-08T11:49:00.721637187Z
Build Git Describe:  VERGEN_IDEMPOTENT_OUTPUT
Commit SHA:          VERGEN_IDEMPOTENT_OUTPUT
Commit Date:         None
Commit Branch:       None
Cargo Target Triple: aarch64-unknown-linux-ohos
Typst Version:       0.12.0
Typst Source:        git+https://github.com/Myriad-Dreamin/typst.git?tag=tinymist-v0.12.0#58426a90a7ef721738a01be09793d33e55eb75a9
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinymist-0.12.2-ohos-aarch64.tar.gz | 待生成 | 预编译包 |

## 注意事项

- tinymist 是 Rust 项目，使用 cargo 构建系统而非 autotools
- SSL证书问题：平台 HTTPS 验证不通过，需手动下载或 curl -kL
---

**编译结束**: 2026-06-08 20:34
**最终状态**: built
