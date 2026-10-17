# DRAFT-ismrmrd-1.7.0-boost-test-header-only-ohos — Boost.Test 纯头文件模式恢复上游测试（路径 B 候选）

> 配对条目：`knowledge/drafts/DRAFT-ismrmrd-1.7.0-boost-test-header-only-ohos.kv`
> 来源：ismrmrd 1.7.0 R01 适配（pc4-26，2026-09-18）

## 问题

在 HarmonyOS PC 上编译 ismrmrd 1.7.0 时，上游测试（Boost.Test 框架，25 个独立
用例）被静默跳过，随后手工链接测试二进制报错：

```
undefined symbol: boost::test_tools::tt_detail::print_log_value<bool>::operator()
```

根因链条：

1. ohpcd 制品仓的 boost/1.84.0 是**裁剪发布**：只包含头文件 +
   libboost_filesystem / iostreams / program_options / regex 四个静态库，
   **没有 libboost_unit_test_framework**。
2. 上游 `tests/CMakeLists.txt` 用
   `find_package(Boost 1.43 COMPONENTS unit_test_framework)` 探测；找不到库时
   直接 `return()` **跳过全部测试**（不是编译报错，容易漏检）。
3. 若忽略跳过、直接以普通 `unit_test.hpp` 头文件模式编译，链接期才暴露
   `print_log_value` 等实现符号缺失。

## 根因

- Boost.Test 自 **1.64** 起支持**纯头文件模式**：不链接编译库即可运行全部用例，
  但实现（含 `print_log_value` 特化）必须由 `boost/test/included/unit_test.hpp`
  在定义 `BOOST_TEST_MODULE` 的那个 TU 中引入；普通 `unit_test.hpp` 只声明不实现。
- 上游 CMake 的组件探测（`unit_test_framework`）把「测试框架库缺失」处理成
  「测试整体跳过」，掩盖了本可运行的用例。

## 最小本地解决 / 边界

```cmake
# tests/CMakeLists.txt 补丁要点（0001-tests-CMakeLists.txt.patch）
# 1) 去掉 COMPONENTS unit_test_framework 硬要求，仅需头文件路径：
#    if (NOT BOOST_INCLUDE_DIR)
#        find_package(Boost 1.43 QUIET)
#        set(BOOST_INCLUDE_DIR ${Boost_INCLUDE_DIR})
#    endif ()
#    if (NOT BOOST_INCLUDE_DIR) ... return() ... endif ()
# 2) 不再 add_definitions(-DBOOST_TEST_DYN_LINK)
# 3) target_link_libraries(test_ismrmrd ismrmrd)   # 不链 Boost_LIBRARIES
```

```cpp
// test_main.cpp 补丁要点（0002-tests-test_main.cpp.patch）
#define BOOST_TEST_MODULE "ISMRMRD Unit Tests"
#include <boost/test/included/unit_test.hpp>   // 仅 BOOST_TEST_MODULE 所在 TU
```

```bash
# 若同时遇到 OHOS libc 未声明 pthread_setcancelstate（sp_thread_sleep.hpp）：
cmake ... -DCMAKE_CXX_FLAGS=-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE
# 注意真实宏名是 BOOST_SP_NO_PTHREAD_SETCANCELSTATE（E507 记录的
# BOOST_SP_THREAD_SLEEP_NO_PTHREAD_SETCANCELSTATE 与 sp_thread_sleep.hpp 不同）
```

适用边界 / 反例：

- Boost.Test < 1.64 不支持头文件模式，必须链接编译库。
- 制品仓已有 `unit_test_framework` 库时，优先直接链接（本方案是降级路径）。
- 定义了 `BOOST_TEST_DYN_LINK` 或依赖动态链接特性时不适用（本方案特意不定义）。
- 多个 TU 只允许一个 `included` 变体（`BOOST_TEST_MODULE` 所在 TU），其余 TU
  保持普通 `unit_test.hpp`。
- 头文件模式把框架实现编进该 TU，编译时间会上升。

## 验证结果

```text
Running 25 test cases...
25 test cases out of 25 passed
7151 assertions out of 7151 passed
*** No errors detected
```

- `make check`（BUILD_TESTS=ON，手动编译）：25/25 通过
- conan-verify G2（配方内 BUILD_TESTS=ON + BOOST_INCLUDE_DIR 注入）：通过
- 双口径：源码声明 25 = 当前配置可执行 25 = 实际通过 25（100%），无未实例化项
- 日志 SHA-256：12414efece69528b43afc836267ebf062096aaf7f7851e0a5243ad44ae197f90
  （`/storage/Users/currentUser/tmp/ismrmrd-upstream-tests.log`）

## 查重与关系

- exact_duplicate=false、causal_duplicate=false、trigger_overlap=E507/E127（部分）、
  solution_overlap=部分（E507 是能力探测+目标级宏，本方案是头文件模式+find_package 松绑）、
  combination_novelty=true、boundary_novelty=true、test_migration_novelty=true。
- similar_to=[E507, E127]；conflicts_with=[E507]（两方案可互相替代，E507 更复杂）。
- 路径决定：**new_draft（路径 B 知识库扩展）**，与 ismrmrd 归档同 PR 交付。
