# mdbook-mermaid

mdbook-mermaid 是一个 mdBook 预处理器，支持在 mdBook 文档中渲染 Mermaid.js 流程图和图表。

## 描述
mdbook-mermaid 允许你在 mdBook 生成的文档中使用 Mermaid.js 语法来创建流程图、序列图、甘特图等图表。它作为 mdBook 的预处理器工作，在渲染书籍时将 Mermaid 代码块转换为可交互的图表。

## 已编译版本
- 0.17.0 (2026-06-04)

## 依赖
- rust/1.85.0

## 特性
- 支持 Mermaid.js 所有图表类型
- 与 mdBook 集成使用
- 纯 Rust 实现，无 Node.js 依赖

## 使用方法
```bash
# 在 book.toml 中添加
[preprocessor.mermaid]

# 构建
mdbook build
```

## 注意事项
- 编译时使用了 --ignore-rust-version 绕过 MSRV 检查（实际兼容）