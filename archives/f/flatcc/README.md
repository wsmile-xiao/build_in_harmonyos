# flatcc

[FlatBuffers](https://google.github.io/flatbuffers/) Compiler and Library in C for C.

## 项目简介

flatcc 是一个高性能的 FlatBuffers 编译器和运行时库，完全用 C 语言编写。它支持：

- FlatBuffers schema (.fbs) 解析与编译
- 自动生成 C 语言 reader/builder/verifier 代码
- JSON 解析与打印
- 反射（Reflection）支持
- 与 Google FlatBuffers 格式完全兼容

## 许可证

Apache License 2.0

## 项目地址

https://github.com/dvidelabs/flatcc

## 可用版本

| 版本 | 状态 | 编译日期 | 构建系统 | 预编译包 |
|------|------|---------|---------|---------|
| 0.6.1 | published | 2026-06-17 | cmake | ✅ flatcc-0.6.1-ohos-aarch64.tar.gz (1.5M) |

## 安装后包含

| 路径 | 内容 |
|------|------|
| `~/usr/local/bin/flatcc` | FlatBuffers schema 编译器 (326K) |
| `~/usr/local/lib/libflatcc.a` | 编译器核心静态库 (479K) |
| `~/usr/local/lib/libflatccrt.a` | 运行时静态库 (196K) |
| `~/usr/local/include/flatcc/` | 63 个头文件（含 portable/reflection/support 子目录） |
