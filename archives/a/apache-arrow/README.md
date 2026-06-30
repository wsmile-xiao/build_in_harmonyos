# Apache Arrow

Apache Arrow 是一个跨语言的内存数据格式，用于高效的数据分析系统。

## 简介

Apache Arrow 定义了一种列式内存格式，用于在现代硬件（CPU、GPU）上高效地进行分析和数据处理操作。Arrow 内存格式支持零拷贝读操作，无需序列化即可在不同系统间共享数据。

## 编译版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 24.0.0 | built | cmake | 2026-05-26 |

## 主要功能

- **列式内存格式**：高效的列式数据存储
- **IPC 协议**：跨进程、跨语言数据交换
- **Compute API**：数据计算操作（过滤、聚合、投影等）
- **Parquet 支持**：Parquet 文件读写
- **零拷贝**：无需序列化的数据共享

## 依赖关系

### 编译依赖
- cmake >= 3.16
- clang/clang++

### 内嵌依赖（vendored）
- xsimd 14.0.0
- mimalloc 3.2.7

## 使用方法

### CMake 项目集成

```cmake
find_package(Arrow REQUIRED)
target_link_libraries(your_target arrow_shared)
```

### pkg-config

```bash
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
pkg-config --cflags --libs arrow
```

## 源码说明

**重要**：Apache 官方发布的 `apache-arrow-{version}.tar.gz` 仅包含 Arrow GLib（C 绑定），不包含 Arrow C++ 核心库。

完整的 Arrow C++ 源码需从 GitHub 获取：
```
https://github.com/apache/arrow/archive/refs/tags/apache-arrow-{version}.tar.gz
```

## 编译配置（24.0.0）

```bash
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_BUILD_TYPE=Release \
      -DARROW_BUILD_TESTS=OFF \
      -DARROW_BUILD_SHARED=ON \
      -DARROW_BUILD_STATIC=ON \
      -DARROW_IPC=ON \
      -DARROW_MIMALLOC=ON
```

## 注意事项

1. 必须设置 `CMAKE_SYSTEM_PROCESSOR` 与目标架构匹配
2. 编译耗时较长（约 12 分钟）
3. 动态库需要 ELF 签名才能在 HarmonyOS 上执行

## 相关链接

- 官网：https://arrow.apache.org/
- GitHub：https://github.com/apache/arrow
- 文档：https://arrow.apache.org/docs/