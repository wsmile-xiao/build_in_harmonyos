# xenium 0.0.2 适配笔记（HarmonyOS PC / OpenHarmony）

## 定位

- xenium 是 header-only 的 C++17 并发数据结构与内存回收算法库（MIT）。
- 上游: https://github.com/mpoeter/xenium (tag v0.0.2)
- 无强制第三方依赖；上游 CI 实测支持 gcc8/clang9/VS2017。

## 编译环境

- 构建系统: cmake（上游 CMakeLists 只构建 gtest 测试与 benchmark，库本体为纯头文件）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, libc++)
- Conan: 2.29.1（OHOS 适配版，os=OHOS 有效枚举）
- 状态: built（设备真机构建与测试通过；release upload 由合并后流水线确认）

## 原生探索步骤（上游测试，设备真机）

```sh
# 源码: v0.0.2 官方 tarball, sha256=05da5e15c4bd600ebd3b5e999a138f39fe8b1a322da899555cd66c4996168d0e
# 子模块(上游测试需要): gtest@695cf7c9, 3rdParty/config@46e0ab2b, 3rdParty/json@879f27ea
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_STANDARD=17 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_CXX_FLAGS="-Wno-error=unused-but-set-variable"
make gtest -j1     # 811 个用例
./gtest
make benchmark -j1 # 上游 benchmark 亦可构建运行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 3.0) 报 Compatibility with CMake < 3.5 has been removed | 设备 cmake 4.1.2 移除 <3.5 兼容 | configure 加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cmake 官方迁移参数，不改源码） |
| 2 | utils.hpp:80 `#error "Unsupported compiler"`（aarch64） | getticks 只实现 sparc/x86_64/MSVC | 0006 补丁：按上游 main 分支实现 XENIUM_ARCH_ARM 分支（cntvct_el0）并在 utils.hpp 引入 detail/port.hpp |
| 3 | generic_epoch_based.hpp:290 std::array 未定义 | 头文件使用 std::array 未包含 <array>；上游依赖 libstdc++ 传递包含，libc++ 下 standalone 包含即失败 | 0005 补丁：补 `#include <array>`（上游 main 分支同位置已含该头文件） |
| 4 | 上游测试 -Werror 下 `called_factory` set-but-unused 报错（clang 15 新警告集） | 上游 CI 用 clang 9 | configure 参数加 `-Wno-error=unused-but-set-variable`，不改上游测试源码 |
| 5 | VyukovHashMap parallel_usage 7/811 失败，`*acc` 恒等于 k+32（跨线程键偏移），8 轮复现 | v0.0.2 先于上游修复：vyukov_hash_map 查找 key 用 relaxed-load、插入/extract/erase 用 relaxed-store，aarch64 弱内存序下并发 rehash/迁移时读到过期槽位；x86 强序掩盖（上游 CI 未发现） | 0003/0004 补丁：回移上游官方修复 1c449ae9（PR #43，2025-07-29 合入 main）——查找路径 key acquire-load、写入路径 key release-store；回移后 811/811 全过（连跑 4 轮稳定） |
| 6 | hardware.hpp `#warning No hardware_pause implementation` | v0.0.2 无 ARM pause 实现 | 0001/0002 补丁：对齐上游 main 的 `asm volatile("yield")` 与 XENIUM_ARCH_ARM 宏 |
| 7 | standalone 包含 impl/vyukov_hash_map.hpp 报 `assert` 未声明 | 头文件使用 assert 但未包含 <cassert>；上游测试经 gtest.h 传递包含未暴露 | 0003 补丁按上游 main b61075bc 补 `#include <cassert>` |

### 已评估但不修改的项（如实记录）

- 上游 1c449ae9 同时把 `#include <xenium/impl/vyukov_hash_map_traits.hpp>` 从顶层
  vyukov_hash_map.hpp 移入 impl 头（重构性质）。v0.0.2 的顶层头已包含该头文件，
  include 位置移动对 standalone 包含无影响，未纳入补丁。
- aligned_object.hpp 缺 `<cstddef>`/`<type_traits>`（上游 b61075bc 曾补）：设备实测
  （clang 15/libc++-ohos，0001-0006 补丁 + 纯净 aligned_object.hpp）test_package 编译运行
  全过（checks=263242 failures=0），传递包含足以补偿，无失败证据，故不修改。
  该文件为 CRLF 行尾，difflib 生成的 LF 上下文补丁也无法通过 `patch` 匹配，进一步
  支持不改。
- 上游 1c449ae9 同时修改了 kirsch_kfifo_queue.hpp 的内存序与 managed_ptr 惰性 accessor 的
  `load_value` 复查（依赖 4ef84daf 引入的 accessor 结构）。设备上 kirsch_kfifo 与 managed_ptr
  相关测试全部通过（无失败证据），且 v0.0.2 的 managed_ptr accessor 为急切加载设计，
  与该复查的适用前提不同，故未纳入补丁，保持最小修复面。

## 源码修改（补丁清单）

| 补丁 | 文件 | 内容 | 类型 |
|------|------|------|------|
| 0001 | xenium/detail/hardware.hpp | aarch64 hardware_pause = ARM yield | portability |
| 0002 | xenium/detail/port.hpp | 增加 XENIUM_ARCH_ARM（__aarch64__） | portability |
| 0003 | xenium/impl/vyukov_hash_map.hpp | 回移上游 1c449ae9：key 内存序 | bugfix |
| 0004 | xenium/impl/vyukov_hash_map_traits.hpp | 回移上游 1c449ae9：compare_trivial_key 签名与 store order | bugfix |
| 0005 | xenium/reclamation/generic_epoch_based.hpp | 补 #include <array> | portability |
| 0006 | xenium/utils.hpp | ARM getticks(cntvct_el0) + include port.hpp | portability |

## 依赖版本

- 无 Conan 依赖（header-only；W0 空依赖集，以上游 CMakeLists find_package 结果实证）
- 工具: cmake 4.1.2 / make 4.4.1 / clang 15.0.4 / ninja（可选）

## 验证结果（设备真机）

```text
上游测试: ./gtest  →  811 tests from 63 test cases, PASSED 811, FAILED 0
          （补丁回移前: PASSED 804 / FAILED 7，全部为 VyukovHashMap/N.parallel_usage）
稳定性:   连续 4 轮全部 811/811 通过；cassert include 修复合入后复跑无回归
benchmark: make benchmark 构建成功，--help 正常输出
test_package: 真实并发消费者测试（对照纯补丁产物编译）
          checks=263242 failures=0，连跑 3 轮计数确定
```

## 注意事项

- 消费方需 C++17 与 pthread（上游 CMakeLists find_package(Threads REQUIRED)）；
  本包不代注入 -lpthread，由消费方构建系统按平台处理（OHOS clang 默认可用）。
- 上游 v0.0.2 的 CMake 不安装头文件（无 install 目标），配方直接打包源码 xenium/ 目录。
- 无命令行产物，不提供 commands.json。
