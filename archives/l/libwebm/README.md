# libwebm

WebM 容器格式的解析和创建库，由 WebM 项目维护。

## 简介

libwebm 是一个纯 C++ 库，提供以下功能：

- **mkvparser**: WebM/Matroska (MKV) 文件解析器
- **mkvmuxer**: WebM 文件创建器/复用器
- **WebVTT**: WebVTT 字幕解析和提取
- **PES/TS**: WebM 到 PES/TS 流转换工具

## 生态位

| 属性 | 值 |
|------|------|
| 语言 | C++ |
| 构建系统 | cmake |
| 许可证 | BSD-3-Clause |
| 依赖 | 无（纯 C++ 库） |

## 鸿蒙适配说明

- 源码无需修改即可在鸿蒙平台编译（无补丁）
- cmake 会检测到 HarmonyOS 为未知平台，不影响编译结果
- 编译产物为静态库 `libwebm.a` 和 17 个头文件
- 源码自带 `build/` 子目录存放 cmake 模块，cmake 输出目录不能使用 `build/` 命名
- 可执行文件（webm_info 等 7 个示例工具）需要 ELF 签名才能在鸿蒙上运行

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.0.0.32 | built | 2026-06-03 |

## 参考

- 源码: https://github.com/webmproject/libwebm
- WebM 规范: https://www.webmproject.org/