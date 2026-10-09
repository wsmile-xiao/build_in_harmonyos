# oscpack 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build . -j4
./OscUnitTests   # 上游官方单元测试
```

注：上游 `cmake_minimum_required(VERSION 2.6)`，CMake ≥4 必须加
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 才能配置。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OscUnitTests 在 `/a_bool` 用例段错误（exit 139） | `OscTypes.h` 假设「非 x86_64 = 32 位平台」：`typedef signed long int32`，而 aarch64 是 LP64（long=8 字节）→ `sizeof(osc::int32)==8`，Release 构建下构造函数的 sanity assert 被 NDEBUG 编译掉，缓冲区管理内部状态被破坏 | 补丁改用 `signed int/unsigned int`（LP32/LP64 通用），见 `0001-osc-OscTypes.h.patch` |
| 2 | 修复 1 后重编报构造函数重复定义 | `int32` 变 `int` 后，`operator<<(int)` 与 `ReceivedPacket(int)` 的守卫 `#if !(x86_64)` 在 LP64 下与 `operator<<(int32)`/`ReceivedPacket(osc_bundle_element_size_t)` 签名重复 | 补丁给两个守卫追加 `&& !defined(__LP64__) && !defined(_LP64)` |
| 3 | CMake ≥4 配置失败 | 上游声明 `cmake_minimum_required(VERSION 2.6)` | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | `cmake.install()` 无产物 | 上游 CMakeLists 完全没有 install 规则 | 补丁追加 install 规则：库 + `osc/`、`ip/` 头文件（保持源码根相对布局，消费者 `#include "osc/OscTypes.h"`） |

## 源码修改

- `patches/0001-osc-OscTypes.h.patch` — LP64 int32/uint32 typedef 修复（核心）
- `patches/0001-osc-OscOutboundPacketStream.h.patch` — LP64 下排除重复的 `operator<<(int)`
- `patches/0001-osc-OscReceivedElements.h.patch` — LP64 下排除重复的 `ReceivedPacket(int)` 构造函数
- `patches/0001-CMakeLists.txt.patch` — 追加 install 规则

## 依赖版本

无第三方依赖（纯 C++，POSIX socket 来自 libc）。

## 验证结果

```bash
# 上游单元测试（构建后直接运行）
./OscUnitTests
# → 91 tests run, 91 passed, 0 failed

# UDP 回环收发（OscReceiveTest 先起，OscSendTests 后跑）
./OscReceiveTest &   # 收到 /an_int64 /a_time_tag /a_double /a_string 等全部消息
./OscSendTests       # exit 0
```

## 注意事项

- 头文件 include 路径是源码根相对布局（`"osc/OscTypes.h"`、`"ip/IpEndpointName.h"`），
  消费者 include 目录应为 `${prefix}/include`，不要把 `osc/`、`ip/` 平铺。
- 字节序：OscHostEndianness.h 通过 `__BYTE_ORDER__` 自动探测，aarch64 OHOS 无需额外宏。
- 库名为 `oscpack`（target `oscpack::oscpack`）。
---

**编译结束**: 2026-09-29 18:59
**最终状态**: built
