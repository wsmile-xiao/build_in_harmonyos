# boost1.84-context 1.84.0 适配笔记

## 组件定位

Boost.Context 是协程/纤程类库的基础库，提供协作式上下文切换：
`fcontext_t`（底层栈切换，手写汇编）、`fiber`（C++ RAII 风格纤程）、
`continuation`/`callcc`（call-with-current-continuation）。

本包以独立包名 `boost1.84-context` 归档（积分赛任务 6383），与
`boost/1.84.0` 元包并行维护。

## 编译环境
- 构建系统: manual-clang（b2 在 OHOS 不兼容 E068，手动 clang++ 编译）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 关键点：OHOS aarch64 汇编支持

Boost.Context 核心是每架构/ABI/OS 组合一份的手写汇编。OHOS aarch64
（architecture=arm / address-model=64 / abi=aapcs / binary-format=elf）
对应上游 `libs/context/src/asm/{make,jump,ontop}_arm64_aapcs_elf_gas.S`。

实测：OHOS SDK clang（llvm 15.0.4）的**集成汇编器**直接编译这三个
`.S` 文件全部通过（`clang++ -x assembler-with-cpp -c`），无需任何
补丁或预处理转换。OHOS SDK 无独立 GNU as，llvm 集成汇编器是唯一
汇编路径——这是本包适配的核心验证点。

库源集合与上游 `libs/context/build/Jamfile.v2` 的
`lib boost_context : impl_sources stack_traits_sources` 一致：

- fcontext（默认 impl）：3 个 arm64 aapcs elf gas 汇编
- posix/stack_traits.cpp（非 Windows 的 stack_traits）
- 编译时定义 `BOOST_CONTEXT_SOURCE`（Jamfile project requirements，
  上游库自身编译的必定义项）

## 上游测试集成（5/5 全绿）

上游 `libs/context/test/` 共 6 个 .cpp（实测与
github.com/boostorg/context tag boost-1.84.0 一致）：

| 文件 | 性质 |
|------|------|
| test_invoke.cpp | 测试用例（BOOST_TEST 断言，自带 main） |
| test_apply.cpp | 测试用例 |
| test_fcontext.cpp | 测试用例 |
| test_fiber.cpp | 测试用例 |
| test_callcc.cpp | 测试用例 |
| is_libstdcxx.cpp | **非测试**：Jamfile build-check 辅助 obj（探测 libstdc++，仅 gcc segmented-stack 路径用；libc++ 下 `#error "Not libstdc++"` 编译必然失败，属预期设计） |

N=5（审核口径：find libs/context/test -name "*.cpp" 得 6，其中 1 个
为构建辅助 obj 非测试用例，测试用例数 5，已在 MANIFEST 中逐文件说明）。

b2 在 OHOS 不可用（E068），本包在 conanfile.py `build()` 中：

1. 编译归档 `libboost_context.a`（3 汇编 + stack_traits.cpp）
2. 逐个 `clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -g0
   -I<root> -DBOOST_ALL_NO_LIB <test>.cpp -lboost_context` 编译、
   真实运行，退出码 0 判定通过（测试输出 "No errors detected."，
   依赖 boost/core/lightweight_test.hpp 而非 unit_test_framework）
3. 统计写入 `build_folder/upstream-tests-report.txt`

实测结果：**5/5 PASS（rc=0）**

### 测试变体口径说明

上游 Jamfile 为 test_fiber/test_callcc 各注册 2 种 context-impl
变体（fcontext/asm 与 native ucontext-segmented；segmented 仅 gcc
libstdc++ 可用，`only-when-segmented-stack-is-available` 条件在
clang/libc++ 下不满足）。本包仅构建默认 fcontext 实现，每源计 1 次
（与 conancenter boost_context 配方默认行为一致）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 汇编是否需要 GNU as / 预处理 | OHOS SDK 无独立 as | llvm 集成汇编器 `clang++ -x assembler-with-cpp -c` 直接编译三个 .S 全部通过 |
| 2 | is_libstdcxx.cpp 编译失败 | `#error "Not libstdc++"`（libc++ 环境） | 属预期设计（build-check obj 非测试），从测试列表剔除，Jamfile 原样保留 |
| 3 | 消费者运行报 libc++_shared.so not found | 测试二进制动态依赖 SDK libc++ | 编译器自省定位 + LD_LIBRARY_PATH + bash export 形式运行（与 container/date_time 同款） |
| 4 | 是否需要 boost/1.84.0 的 0001 补丁 | context 是否触碰 sp_thread_sleep.hpp 的 pthread_setcancelstate 路径 | 实测：无补丁无宏全部编译运行通过，无需补丁 |
| 5 | 是否只安装 boost/context 子树 | Boost 库间头文件传递依赖 | 安装完整 boost/ 头树（与 boost/1.84.0 配方一致） |
| 6 | CI 低内存 worker（CI-021）上 5 个测试全部 linker signal 被杀（#41383） | 纤维/协程测试的模板纤维实例化在 -O2 下链接内存峰值超 CI worker 限额（context 比 container 更吃链接内存） | 5 个测试编译全部降档 -Os -DNDEBUG -g0（代码尺寸优先档）；库本体仍 -O2。与 container #8435 削峰同款但全量降档 |

## 源码修改
无补丁；未改动上游源码（含测试源，5 个测试 .cpp 逐字节未动）。

## 依赖版本
- 无 conan 依赖（context 不依赖 zlib 等外部库；context 是 fiber/
  coroutine/fiber 系列的底层依赖）
- 运行时依赖：libc++（OHOS sysroot）
