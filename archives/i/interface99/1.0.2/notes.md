# interface99 1.0.2 适配笔记

## 编译环境

- 构建系统: header-only（上游 CMake 为 INTERFACE 库；tests/ 为独立 CMake 工程）
- 平台任务: contrib-12572（interface99 1.0.2），claimer Ember5843，认领 2026-09-15T05:46Z
- 目标平台: HarmonyOS PC arm64（clang 15 / musl / libc++），本机原生构建
- 依赖: Metalang99 v1.13.5（interface99.h 的宏引擎，`#include <metalang99.h>` 硬依赖；
  制品仓无此包 → 按上游 FetchContent 锁定版本随包交付头文件）
- 上游: https://github.com/Hirrolot/interface99 （357 stars；tag v1.0.2）
- 源码 sha256: interface99 `8bd007c4…`；metalang99 `f3d1607d…`
- 语言实测（R47 lang-preflight）: 头文件库（interface99.h 单头 + tests/examples C99 源）

## 源码面貌（摸底结论）

- 交付形态: `interface99.h`（单头）+ 依赖头 `metalang99.h`、`metalang99/*.h`
- 上游 tests/：8 个测试程序（basic_tests/vcalls/decl_impl/metalang99_compliant/
  superinterfaces/default_impl/version/extern_impl），独立 CMake 工程、默认构建不含、
  GCC/Clang 硬编码 `-fsanitize=address`
- 上游 CMake：FetchContent 拉 Metalang99 v1.13.5（configure 期联网）→ 本配方跳过其 CMake，
  直接安装头文件，规避构建期联网

## 移植要点

1. **包自包含**：消费者 `#include <interface99.h>` 会连带包含 `<metalang99.h>`，因此包内
   同时安装两套头（include/ 平铺），两个 LICENSE 分别改名落 licenses/
2. **上游测试全跑**（路径 A 硬要求）：build() 用 `tools.build:compiler_executables` 的 CC
   以 `-std=c99 -I<源根> -I<metalang99-src>` 逐程序编译并执行 8 个测试；**剥离 ASan**
   （OHOS musl 无 ASan 运行库——平台差异，PR 已归因），断言型测试以退出码为判据
3. 防撞：远端无 interface99 遗留分支；制品仓无 atomic_queue 之外的同名发布
   （扫描中发现 atomic_queue/1.9.2 已发布，故跳过同上游的 libatomic-queue 1.7.2 任务——
   否决线 1 实战案例）

## 状态

- [x] 配方四件套
- [x] 设备实机 conan create + conan-verify（G0-G3）+ 上游测试 8/8 + 消费者测试 5 断言
- [x] push / PR / 平台绑定 / 提审
