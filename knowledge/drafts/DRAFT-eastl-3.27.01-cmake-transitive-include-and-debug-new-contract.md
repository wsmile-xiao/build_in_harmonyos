# DRAFT-eastl-3.27.01-cmake-transitive-include-and-debug-new-contract — 编译型库头文件依赖的传递 include 下发与 debug new 消费者契约

## 问题现象

EASTL 3.27.01（Electronic Arts STL，编译型 C++ 库，`source/*.cpp` -> libEASTL）在
OHOS aarch64 + Conan 2.29 适配时，消费者侧（test_package）出现两类真实错误：

```
# C1：消费者只 find_package(eastl) 时，EASTL 公开头文件内部的 EABase include 丢失
In file included from .../include/EASTL/vector.h:36:
.../include/EASTL/internal/config.h:61:11: fatal error: 'EABase/eabase.h' file not found

# C2：链接期缺少 EA 风格的 debug operator new[]
ld.lld: error: undefined symbol: operator new[](unsigned long, char const*, int, unsigned int, char const*, int)
>>> referenced by test.cpp:(main)
```

## 根因分析

**C1**：EASTL 是编译型库，其公开头文件（`include/EASTL/*.h`）大量使用
`#include <EABase/eabase.h>` 等依赖库头文件。适配时，上游 `FetchContent EABase` 被改为 Conan 依赖
`eabase/0699a15`（R39：禁止构建期 git fetch）。但消费者 test_package 仅执行 `find_package(eastl)` 并链接
`eastl::eastl` 时，CMakeDeps 生成的 `eastl-Target-release.cmake` 中
INTERFACE_LINK_LIBRARIES 虽已含 `eabase::eabase`，eabase 作为**传递依赖**生成的
`eabase_INCLUDE_DIRS_RELEASE` 却为空——仅头文件包（`no_copy_source=True` +
`package_id()` 清空）的 include 目录没有真正传递到编译命令行。库本体构建（eabase
为直接依赖）正常，只有消费者失效，属于“包公开头文件依赖另一包头文件”的传递 include 转发问题。

**C2**：`EASTL/allocator.h` 在 `!EASTL_DLL` 下声明了 EA 风格 debug
`operator new[](size_t, const char*, int, unsigned, const char*, int)`（含对齐变体），
注释明确说明“由应用负责定义”；上游 EASTLTest 通过 EAMain 提供该定义。EAMain 尚未发布到 ohpcd 时，
消费者（test_package 使用 eastl::vector/string）链接即报未定义符号。

## 修复方案

1. **配方传递 include**：eastl conanfile.py 的 `package_info()` 增加
   `self.cpp_info.requires = ["eabase::eabase"]`，将仅头文件依赖的 include 目录接入 `eastl::eastl` 的传递链。
2. **test_package 显式声明依赖**：执行 `find_package(eabase REQUIRED)`，并调用
   `target_link_libraries(test_xxx eastl::eastl eabase::eabase)`（在消费者侧将
   eabase 从传递依赖改为直接依赖，与库本体构建行为一致）。
3. **定制 debug new 契约**：test_package 按 allocator.h 中的签名提供两个基于 malloc 的
   no-op debug `operator new[]` 重载（忽略 pName/flags/debugFlags/file/line 实参）。
4. 上游测试族（EAAssert/EAStdC/EAMain/EATest/EAThread）未发布导致的 EASTLTest
   链接阻塞属于外部依赖/平台阻塞（E211/E127 已覆盖 pthread affinity/cancel 部分），
   不在本条目范围内；恢复条件是分析端先行发布测试族。

## 验证

```
conan create archives/e/eastl/3.27.01 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 修复前：G2 FAIL（C1 EABase/eabase.h not found；随后修正 C2 undefined symbol）
# 修复后：G2 PASS, G3 PASS, G4 PASS; test_package ctest 2/2 Passed:
#   test_eastl                1/2 ... Passed
#   harmonyos_specific_test   2/2 ... Passed  0.03 sec
```

## 适用边界与反例

- 适用范围：公开头文件直接 `#include <dep/...>` 的编译型 C++ Conan 库，dep 为仅头文件包
（EA 系 eastl→eabase 最典型）；L0 库类型均可能遇到，不限于 OHOS。
- 反例/边界：若仅头文件库自身的 include 不依赖其他包头文件，则不会遇到此问题；依赖包为编译型
库时，CMakeDeps 传递 include 通常正常（存在实际 libdirs）；纯运行时 libdirs 传递见 E499，
与本条目（编译期 include）的机制不同。

## 与既有知识的查重差异

| 维度 | 结论 |
|---|---|
| exact_duplicate | 否（E447/E498/E499/E217 均无此机制组合） |
| causal_duplicate | 否（E447 为 vendored Find module 转发；E498 为包自身 includedirs 契约；E499 为运行时 libdirs） |
| trigger_overlap | 部分重叠（均由“消费者找不到依赖头文件/运行时库”触发） |
| solution_overlap | 部分重叠（都涉及 include/依赖显式化，但本条目采用 cpp_info.requires + test_package 显式 find_package 的双重保障） |
| combination_novelty | 是（明确指出编译型库 + 仅头文件依赖 + CMakeDeps 传递失效的根因与修复组合） |
| boundary_novelty | 是（debug operator new[] 应用侧契约在 ohpcd/EAMain 未发布场景下的实际应用） |
| test_migration_novelty | 否（无上游测试迁移） |

关系：similar_to=[E447,E498,E499,E217]；caused_by/prerequisite_of/conflicts_with=无。

---
*根据 eastl 3.27.01 R02 适配轮的真实日志生成（通过 conan-verify G2 修复前后对比验证）*
