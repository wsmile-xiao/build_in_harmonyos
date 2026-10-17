# libprotoc

Protocol Buffers 的编译器库（`libprotoc`）。

## 描述

`libprotoc` 是 [Protocol Buffers](https://github.com/protocolbuffers/protobuf) 项目中的
C++ 编译器库，提供 `.proto` 解析、描述符构建与代码生成器框架。

> **注意**：`libprotoc` 没有独立的上游仓库。它是 protobuf 源码树中的 CMake 目标
> （`cmake/libprotoc.cmake`），源码位于 `src/google/protobuf/compiler`。本适配从
> protobuf 官方 release 源码包构建，最终只交付 `libprotoc` 及其运行时依赖。

## OpenHarmony 适配

- 构建系统：CMake
- 目标平台：HarmonyOS PC（aarch64-linux-ohos, musl）
- 交付内容：`libprotoc.a` + 其传递依赖（`libprotobuf.a`、`libupb.a`、`libprotobuf-lite.a`）
  + 公共头文件 + CMake 导出配置
- **不含** `protoc` 命令行工具（本包只交付编译器库）

### 关键适配点

- `protobuf_BUILD_LIBPROTOC=ON`：31.1 默认关闭该库，需显式开启
- googletest 由配方单独拉取（31.1 源码树不含内置 googletest），并通过
  `protobuf_GTEST_SOURCE_DIR` 接入
- 打包前剥离 `protoc` 及 `protoc-gen-*` 工具目标，同步清理 CMake 导出配置中
  对这些工具目标的引用，保证消费者 `find_package(Protobuf CONFIG)` 可用

## 版本

| 版本 | 状态 | 构建日期 |
|---|---|---|
| 31.1 | built | 2026-09-22 |

## 消费示例

```cmake
find_package(Protobuf CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE protobuf::libprotoc)
```

## 相关

- 需要 `protoc` 命令行工具时，请使用 **protobuf** 适配（如 `protobuf/33.6.1`、`protobuf/34.1`）
- 上游仓库：https://github.com/protocolbuffers/protobuf
