# serialize

[serialize](https://github.com/mas-bandwidth/serialize)（作者 Glenn Fiedler，Más Bandwidth LLC）——
单头文件 C++ 位打包序列化库，用于把游戏网络协议的状态数据压到逐位精度（BSD-3-Clause）。

## 简介

`serialize.h`（约 3.2k 行）提供 `serialize::BitWriter` / `serialize::BitReader` 原始位流，
以及 `WriteStream` / `ReadStream` / `MeasureStream` 三态统一的 `Serialize` 模板路径。核心能力：

- `bool` 只占 1 bit；任意 `[1,64]` 位宽的无符号整数按需写位
- 有符号整数按 `[min,max]` 区间只写所需位数；`serialize_int_relative` 以参考值为基准写差值
- 浮点、压缩浮点（量化区间）、double、字符串、宽字符串、字节数组
- 任意位置按字节对齐（`serialize_align`）
- 同一份 `Serialize` 函数同时支持读/写/测量（模板 + 宏）
- 库内定义 wire format 为小端（"network byte order"），跨平台字节级一致

## 功能概述

- 逐位精度整数编码 + zigzag 有符号映射
- 压缩浮点（`serialize_compressed_float`）与相对整数编码
- 统一的流抽象：`WriteStream` / `ReadStream` / `MeasureStream`
- 无异常错误处理：读取非法数据返回 `false`，便于处理不可信网络输入

## OHOS 适配要点

- **单头文件库**：无链接产物，上游 CMake 暴露 INTERFACE target `serialize`（别名
  `serialize::serialize`），只传递 include 路径；本配方经 `CMake.install()` 保留上游安装布局
  （`include/serialize.h` + `lib/cmake/serialize/serialize-config.cmake`）。
- **字节序检测**：`serialize.h` 首选编译器内建 `__BYTE_ORDER__`；OHOS aarch64 clang 15 已定义该宏，
  因此开箱解析为 `SERIALIZE_LITTLE_ENDIAN=1`，无需补丁或额外宏。头文件的架构宏回退链不含
  `__aarch64__`/`__arm__`，仅在编译器不提供 `__BYTE_ORDER__` 时才需显式 `-DSERIALIZE_LITTLE_ENDIAN`。
- **wchar_t 宽度**：OHOS/musl 的 `wchar_t` 为 4 字节，非 BMP 码点（如 `U+1F600`）可完整往返；
  线上格式固定 32 bit/字符，与 2 字节平台保持兼容。
- **上游测试**：上游自带 CTest 入口（`test.cpp` → `bin/test`，覆盖 17 个测试函数 / 175 项断言），
  配方 `build()` 保留该入口，跨编译时交给目标平台执行。

## 依赖关系

- 编译依赖：无（header-only，仅 C++ 标准库；C++11 及以上）
- 运行依赖：无

## 构建与验证

```bash
# OHOS aarch64 交叉构建
conan create archives/s/serialize/1.4.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# 本机原生构建（W3 路径，含上游 CTest + test_package 2 项）
conan create archives/s/serialize/1.4.4 -pr:h=default -pr:b=default --build=missing
```

## 参考资料

- 上游仓库: https://github.com/mas-bandwidth/serialize
- 上游 tag: v1.4.4（commit `3a066b8bc8798b6b6dfbfecfd348ad63f82c3bd4`）
- 构建说明: https://github.com/mas-bandwidth/serialize/blob/main/BUILDING.md
