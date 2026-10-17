# libucl

**描述**: Universal Configuration Library (UCL) — 通用配置库，提供类似 nginx 配置语法的解析器，支持 JSON、YAML、MsgPack 等多种格式。

**许可证**: BSD-2-Clause

**主页**: https://github.com/vstakhov/libucl

## 已编译版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 0.9.2 | built | CMake | 2026-09-01 |
| 0.9.4 | published | CMake | 2026-06-26 |

## 产物说明

- **lib**: libucl.a（静态库，9 个目标文件）
- **include**: ucl.h（C 接口）、ucl++.h（C++ 封装）
- **无 Conan 包依赖**: 自包含 uthash、klib 等内嵌库；静态链接消费者还需系统数学库 `m`
