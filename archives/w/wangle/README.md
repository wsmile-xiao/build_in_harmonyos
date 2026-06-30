# wangle

wangle 是 Facebook 开发的 C++ 网络库，提供异步网络编程框架。

## 概述

wangle 是一个基于 folly 的 C++ 异步网络库，提供服务框架和 RPC 功能。它构建在 folly 和 fizz 之上，提供高级网络抽象，简化异步网络编程。

### 主要特性
- 基于 folly 的高性能异步 I/O
- 支持 TLS/SSL 安全连接（依赖 fizz）
- 提供客户端/服务端框架
- Pipeline 编程模型
- 内置负载均衡和服务发现

## 编译状态

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| v2026.05.18.00 | built | 2026-05-26 |

## 依赖

### 核心依赖
- folly v2026.05.18.00
- fizz v2026.05.18.00
- openssl 3.5.6
- boost 1.74.0 (context, filesystem, program_options, regex, thread)

### 辅助依赖
- glog
- double-conversion 3.3.0
- libevent
- gflags
- zlib 1.3.1
- libsodium
- fmt

## 使用方式

### CMake 集成

```cmake
find_package(wangle CONFIG REQUIRED)
target_link_libraries(your_target wangle)
```

### 编译选项
- `BUILD_TESTS=OFF` - 禁用测试构建（推荐）
- `BUILD_EXAMPLES=OFF` - 禁用示例构建（推荐）

## 注意事项

1. **依赖顺序**: 需要先编译 folly 和 fizz，wangle 依赖这两个库
2. **Boost 查找**: CMake 配置时会在 folly 之前查找 Boost，避免目标重复定义
3. **CMake Policy**: 已设置 CMP0167 为 NEW，兼容 CMake 3.31+

## 编译说明

详细编译步骤和问题解决方案请参考各版本的 notes.md。

## 许可证

Apache License 2.0
