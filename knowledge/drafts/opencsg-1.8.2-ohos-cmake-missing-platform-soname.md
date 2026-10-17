# OHOS CMake 缺 Platform 模块：共享库无版本化 SONAME

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-ohos-cmake-missing-platform-soname.kv` 成对。

## 现象

1. CMake configure 时输出：

```text
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org
```

2. 设备 `conan create` 得到的共享库没有 SONAME，且消费者二进制的 `DT_NEEDED` 是
   **绝对路径**而不是库名：

```text
# 包内只有一个文件，无 .so.N / .so.N.M 符号链接链
lib/libopencsg.so
# 消费者 test_opencsg
NEEDED  <...>/p/lib/libopencsg.so     ← 绝对路径
```

## 根因

OHOS 上 CMake 没有 `Platform/HarmonyOS.cmake`。平台规则缺失，使
`add_library(... SHARED)` 配合 `set_target_properties(... VERSION ... SOVERSION ...)` 时
不生成版本化文件名，也不向链接器传 `-Wl,-soname`。上游
`set_target_properties(opencsg PROPERTIES VERSION ... SOVERSION ...)` 本身完全正确。

## 最小复现（证明是平台限制，与库无关）

```cmake
cmake_minimum_required(VERSION 3.11)
project(t LANGUAGES CXX VERSION 1.8.2)
message(STATUS "PV=[${PROJECT_VERSION}] PVM=[${PROJECT_VERSION_MAJOR}]")  # → PV=[1.8.2] PVM=[1]
add_library(t SHARED t.cpp)
set_target_properties(t PROPERTIES VERSION ${PROJECT_VERSION} SOVERSION ${PROJECT_VERSION_MAJOR})
```

设备 hnp cmake 4.1.2 构建结果：只产出 `libt.so`，`llvm-readelf -d libt.so | grep -i soname`
**无输出**。对照：autotools 构建的 `libpam.so` 有 `SONAME=libpam.so.0`。
另外，同一份 opencsg 源码用 OHOS SDK 工具链 + Ninja 在本机交叉编译时**有**
`SONAME=libopencsg.so.1`——说明差异来自设备 CMake 的平台模块缺失，而非源码或补丁。

## 处理策略

- ❌ 不要在单库里手写 `-Wl,-soname` 之类的平台级 hack：偏离上游、难以维护、
  无法惠及其它 CMake 库。
- ✅ 记录为已知限制；由基础设施补齐 `Platform/HarmonyOS.cmake`，或在 CMakeToolchain /
  toolchain file 里统一注入 soname（一次修复覆盖所有 CMake 共享库）。
- CI 的 L0/L1/L2/L4/L5 门禁不检查也不拒绝该差异，不影响包通过。

## 适用范围

所有在 OHOS 上用 CMake 构建的**共享库**。静态库与可执行文件不受影响。
下游若依赖“通过 SONAME 做 ABI 版本切换”的能力，在 OHOS 上当前不可用。
