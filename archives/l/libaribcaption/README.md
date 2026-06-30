# libaribcaption

Portable ARIB STD-B24 Caption Decoder/Renderer — 便携式 ARIB STD-B24 字幕解码/渲染库

## 简介

libaribcaption 是一个便携的 ARIB STD-B24 字幕解码器和渲染器库，主要用于日本 ISDB 数字电视广播的字幕处理。

- **许可证**: MIT
- **语言**: C/C++
- **构建系统**: cmake
- **上游地址**: https://github.com/xqq/libaribcaption

## 功能

- **解码器 (Decoder)**: 解析 ARIB STD-B24 字幕数据流，支持 A-profile (ARIBCC_PROFILE_A) 和 C-profile (ARIBCC_PROFILE_C)
- **渲染器 (Renderer)**: 将解码结果渲染为图像（需 Fontconfig + FreeType，OHOS 环境暂不可用）

## OHOS 适配说明

在 OHOS 平台编译时使用 `-DARIBCC_NO_RENDERER=ON` 禁用渲染器，仅保留解码器功能。渲染器依赖 Fontconfig 和 FreeType，当前 OHOS 环境尚未提供这两个库的预编译包。

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.1.1 | published | 2026-06-12 | 解码器可用，渲染器禁用 |

## 依赖

- 编译时无依赖（renderer 禁用后）
- 若启用 renderer: Fontconfig + FreeType
