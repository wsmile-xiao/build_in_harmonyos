# mdbook-mermaid 0.17.0 适配笔记

## 编译环境
- 构建系统: cargo
- 编译日期: 2026-06-04
- 编译器: rustc 1.85.0
- 状态: published

## 编译步骤

1. cargo build --release --ignore-rust-version
2. 手动 cp target/release/mdbook-mermaid 到 staging/local 安装目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc 1.85.0 不满足 mdbook-core@0.5.0 和 mdbook-preprocessor@0.5.0 的 rust-version=1.88.0 要求 | 依赖包设置了 MSRV 门禁 | 使用 cargo --ignore-rust-version 绕过 MSRV 检查，实际编译无兼容性问题 |

## 源码修改

无源码修改。使用 cargo --ignore-rust-version 运行参数绕过 MSRV 检查。

## 依赖版本

- mdbook-preprocessor 0.5.0
- mdbook-core 0.5.0
- pulldown-cmark 0.10.3
- clap 4.5.52
- serde_json 1.0.145
- toml_edit 0.15.0
- env_logger 0.11.8
- log 0.4.28
- rustc 1.85.0

## 验证结果

```bash
$ mdbook-mermaid --version
mdbook-mermaid 0.17.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mdbook-mermaid-0.17.0-ohos-aarch64.tar.gz | ~3MB | 预编译包（release） |
| mdbook-mermaid-0.17.0-ohos-aarch64-debug.tar.gz | ~7.4MB | 预编译包（debug） |

## 注意事项

- 编译需要使用 --ignore-rust-version 参数，因依赖包 mdbook-core 和 mdbook-preprocessor 声明 MSRV=1.88.0，但实际在 rustc 1.85.0 上编译无问题
- mdbook-mermaid 是 mdBook 的 mermaid 图表插件，生成 ELF 64-bit aarch64 静态链接可执行文件
- 安装路径: bin/mdbook-mermaid
---

**编译结束**: 2026-06-04 11:54
**最终状态**: published
