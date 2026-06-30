# pdfpc

pdfpc 是一个支持多监视器的 PDF 演示控制台，为 Linux/OpenHarmony 演示提供类似 Keynote/PowerPoint 的功能。

## 描述

pdfpc 支持在主监视器上全屏显示当前幻灯片，同时在次监视器上显示下一张幻灯片预览、时间和笔记。它是学术会议和教学的常用演示工具。

## 已编译版本

- 4.7.0 (2026-05-27)

## 依赖

- poppler-glib (PDF 渲染)
- libgee (数据结构)
- vala (Vala 编译器)

## 特性

- 多监视器演示支持
- 幻灯片笔记显示
- 定时器功能
- 触屏支持

## 使用方法

```bash
# 启动 PDF 演示
pdfpc presentation.pdf
```