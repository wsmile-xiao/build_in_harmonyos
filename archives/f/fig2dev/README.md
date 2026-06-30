# fig2dev

fig2dev 是 Xfig 绘图工具的转换程序，将 .fig 格式文件转换为 EPS、PDF、PNG、SVG 等多种输出格式。

## 描述

fig2dev 是 transfig 包的核心组件，用于将 Xfig 创建的矢量绘图转换为各种格式。它支持 LaTeX/PostScript 嵌入，是学术论文和技术文档中嵌入矢量图的重要工具。

## 已编译版本

- 3.2.9a (2026-05-27)

## 依赖

- libiconv
- zlib

## OHOS 适配说明

- configure 中 umask 077 导致 HMDFS 权限问题（E050），已修复为 umask 022

## 使用方法

```bash
# 转换 fig 文件为 PDF
fig2dev -L pdf input.fig output.pdf
```