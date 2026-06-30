# apitrace

apitrace 是一个 API 调用追踪框架，用于记录和重放 OpenGL、Direct3D 及其他图形 API 的调用。

## 描述

apitrace 可以追踪应用程序对图形 API 的调用，生成可回放的 trace 文件。它支持 OpenGL、Direct3D、Vulkan 等 API，是图形调试和性能分析的必备工具。

## 已编译版本

- 14.0 (2026-05-30)

## 特性

- 记录和回放图形 API 调用
- 支持 OpenGL、Direct3D、Vulkan
- 生成可分析的 trace 文件
- 性能分析和调试支持

## 使用方法

```bash
# 追踪 OpenGL 应用
apitrace trace <application>
# 回放 trace
apitrace replay <trace_file>
```