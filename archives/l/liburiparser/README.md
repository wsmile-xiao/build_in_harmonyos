# liburiparser

## 简介

liburiparser 是一个严格遵循 RFC 3986 标准的 URI 解析和处理库，使用 C99 编写。

## 主要特性

- 严格遵循 RFC 3986（最新的 URI RFC 标准）
- 解析、引用解析、引用创建、重新组合
- 支持语法规范化
- 快速（线性时间复杂度）
- 支持 char 和 wchar_t 字符串
- 无外部依赖
- BSD 许可证

## OHOS 适配要点

- 构建系统：CMake（configure 脚本为包装器）
- 使用 `-DURIPARSER_BUILD_DOCS=OFF` 禁用文档生成（需要 Doxygen）
- 默认编译为共享库（liburiparser.so）
- 二进制工具：uriparse（URI 解析工具）

## 依赖

无外部依赖。

## 版本信息

- 当前版本：1.0.2
- 发布日期：2026-05-09
- 包含安全修复

## 已知问题

- configure 脚本使用 bash 特有语法，在非 bash shell 下可能失败
- 推荐直接使用 cmake 配置：`cmake -DCMAKE_INSTALL_PREFIX=/path ..`
