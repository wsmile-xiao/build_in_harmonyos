# Tesseract OCR

## 简介

Tesseract 是一个开源的 OCR（光学字符识别）引擎，支持 100 多种语言的文字识别，广泛用于文档数字化、图像文字提取等场景。

## 功能概述

- **文字识别**：支持 100+ 语言的 LSTM 神经网络识别引擎
- **输出格式**：纯文本、hOCR（HTML）、PDF、TSV、ALTO XML 等多种输出
- **图像预处理**：内置页面分割、文字行/词/字符检测
- **API 接口**：提供 C++ (baseapi) 和 C (capi) 两套接口
- **命令行工具**：`tesseract` 命令行工具支持批量识别和管道操作

## OHOS 适配

### 适配要点

1. **SIMD 检测修复**：aarch64 平台需应用 `0001-simddetect.patch`，将 NEON 代码路径从 `#if defined(__aarch64__)` 改为 `#if defined(HAVE_NEON) && defined(__aarch64__)`，避免 HAVE_NEON 未定义时的链接错误
2. **禁用训练工具**：`BUILD_TRAINING_TOOLS=False`（依赖 pango/cairo 不可用）
3. **禁用图形界面**：`GRAPHICS_DISABLED=True`（无头构建环境）
4. **CMake 策略兼容**：`CMAKE_POLICY_VERSION_MINIMUM=3.5`

### 已知问题

- cmake 警告 "System is unknown"（鸿蒙不在 cmake 已知平台列表中），可忽略
- 训练工具不可用（pango/cairo 依赖缺失），不影响核心 OCR 功能
- 词典数据（tessdata）需单独获取

## 依赖

### 编译依赖

- leptonica（通过 `leptonica/1.87.0@ohpcd/stable` 引入）

### 可选依赖（当前已禁用）

- pango/cairo（训练工具，已通过 BUILD_TRAINING_TOOLS=False 禁用）
- libarchive（已禁用）
- libcurl（已禁用）

## 功能验证

```bash
# Conan 构建
conan create archives/t/tesseract/5.3.3/ --build=missing

# CI 验证（L0-L5 全通过）
CI_PACKAGES="archives/t/tesseract/5.3.3" zsh ci/conan/build_and_test.sh

# smoke test
tesseract --version
# 输出: tesseract 5.3.3

# test_package 输出
# tesseract version: 5.3.3
# test tesseract 5.3.3: OK
```

## 参考

- 官方仓库：https://github.com/tesseract-ocr/tesseract
- 文档：https://tesseract-ocr.github.io/
- 语言数据：https://github.com/tesseract-ocr/tessdata
