# librevenge

librevenge 是一个文档格式转换的低级库。

## 描述
librevenge (REVENGE = Reverse Engineering of Generators and Extractors) 是一个用于文档格式转换的基础库，提供抽象接口和流处理功能。它是 libwpd、libwpg 等文档解析库的核心依赖。

## 已编译版本
- 0.0.5 (2026-06-01)

## 依赖
- 无外部依赖（纯 C++ 项目）

## 特性
- 提供文档内容抽象接口 (RVNGDrawingContent, RVNGTextContent, RVNGPresentationContent, RVNGSpreadsheetContent)
- 提供流处理 (RVNGInputStream)
- 提供 SVG 生成器 (RVNGSVGDrawingGenerator)

## 使用方法
作为基础库使用，通常通过 libwpd、libwpg 等上层库间接调用。