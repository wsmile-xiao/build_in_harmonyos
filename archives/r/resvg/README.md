# resvg

resvg 是一个用 Rust 编写的 SVG 渲染库和命令行工具。

## 描述

resvg 可以将 SVG 文件渲染为 PNG 或其他位图格式，支持 SVG 1.1 规范的大部分特性。它旨在提供高质量的 SVG 渲染，同时保持性能和安全性。

## 已编译版本
- 0.47.0 (2026-05-26)

## 依赖
- Rust 工具链 (1.95.0)
- zlib

## 特性
- SVG 1.1 规范支持
- 文本渲染（system-fonts, memmap-fonts）
- 高质量抗锯齿
- 命令行渲染工具
- 可作为 C 库集成

## 使用方法
```bash
# 渲染 SVG 到 PNG
resvg input.svg output.png

# 查看版本
resvg --version
```

## 注意事项
- Rust 工具链需要修复 RPATH 和 ELF 签名才能在 OpenHarmony 上运行