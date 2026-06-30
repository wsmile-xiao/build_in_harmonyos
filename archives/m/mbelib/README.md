# mbelib — P25 语音编解码库

mbelib 是一个 C 语言编写的语音编解码库，支持以下 codec：
- **IMBE 7200x4400**：P25 Phase 1 使用的 codec
- **AMBE 7100x4400**：ProVoice 使用的 codec
- **AMBE 3600x2250**：Half Rate vocoder，用于多种无线电系统

> **专利声明**：本源码仅供教育用途。编译生成的可执行文件可能受一项或多项专利保护，使用前请检查专利限制。

## OHOS 适配要点

- CMakeLists.txt 的 `cmake_minimum_required(VERSION 2.6)` 与 CMake 4.x 不兼容，编译时需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 项目自带 gtest/gmock 测试框架，但 ctest 未注册测试，需直接运行 `mbetest`
- mbelib 是纯库项目（生成 libmbe.a/libmbe.so + mbelib.h），无可执行二进制文件

## 编译依赖

无外部依赖。mbelib 是纯 C 库，仅依赖 libc。

## 已编译版本

| 版本 | 状态 | 构建系统 | 日期 | 备注 |
|------|------|----------|------|------|
| 1.3.0 | built | cmake | 2026-06-15 | 需 CMAKE_POLICY_VERSION_MINIMUM=3.5 |

## 参考资料

- 源码仓库：https://github.com/szechyjs/mbelib
- 许可证：ISC
