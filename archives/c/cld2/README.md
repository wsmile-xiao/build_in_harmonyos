# cld2

Google Compact Language Detector 2：对 Unicode UTF-8 文本（纯文本或 HTML/XML）
做概率性语言检测的 C++ 库，可识别 80+ 语言（全表 160 语言），最初为
Chromium 浏览器编写。

## 功能概述

- 检测纯文本或 HTML/XML 文档的主要语言及混合语言占比
- 支持 80+ 语言（libcld2），全表支持 160 语言（libcld2_full）
- 表驱动的朴素贝叶斯分类器，速度快、体积小
- 零外部依赖

## OHOS 适配

- 上游无 configure/CMake，构建复刻官方 `internal/compile_libs.sh`
- 编译器与 C++ 标准来自 Conan 工具链配置（R33）
- 产物：`libcld2.so` + `libcld2_full.so`，头文件位于 `include/cld2/public`

## 依赖关系

- 无外部依赖

## 参考资料

- 源码: https://github.com/CLD2Owners/cld2
