# DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location：OHOS SDK 26 libc++ 缺 <source_location> 头，无条件 include 的 C++20 代码编译失败

> Contributor: tianyi_wang | Status: Draft | Updated: 2026-09-03
> Source: reflect-cpp 0.17.0 HarmonyOS PC 适配（archives/r/reflect-cpp/0.17.0，patches 0001-0010）
> 对应：knowledge/drafts/DRAFT-reflect-cpp-0.17.0-ohos-sdk26-libcxx-missing-source-location.kv

## 现象

OHOS SDK 26.0.0.18 的 clang 15.0.4（配套 libc++，LLVM 15 系）下，凡无条件
`#include <source_location>` 的 C++20 代码全部编译失败：

```text
fatal error: 'source_location' file not found
```

库本体通常不炸：reflect-cpp 的 3 个使用 `std::source_location` 的内部 header
（`rfl/internal/get_field_names.hpp`、`get_type_name.hpp`、
`enums/get_enum_names.hpp`）都有 `#if __has_include(<source_location>)` 守卫，
头缺失时功能静默降级；炸的是**测试文件**——10 个 `tests/*/test_*.cpp` 无条件
include 该头，而 grep 证实测试中 `std::source_location` 实际使用次数为 0，
属纯冗余 include。

隐蔽点：`<source_location>` 是 C++20 特性（P0662），libc++ 在 LLVM 16 才落地该
头；任何 OHOS SDK 15 系 libc++（含 SDK 26 的 clang 15 工具链）都不提供。
"库本体编译通过"不能证明测试/下游消费代码也能过——守卫差异会制造这种分裂。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph（540 条 E*.kv）+ knowledge/drafts（163 对，快照
main@2f60a107，稀疏只读）。
检索词：source_location / std::source_location / libc++ / SDK 26 / missing
header / __has_include / C++20 头缺失。
graph 面 0 精确命中；drafts 面最接近者为
`DRAFT-libcxx15-missing-cpp20-spaceship`（OHOS clang15/libc++ 缺 C++20
`operator<=>` 三路比较）——同为"OHOS SDK 15 系 libc++ 缺 C++20 特性"家族，
但错误签名（`no match for 'operator<=>'` vs `'source_location' file not found`）、
根因（容器 `<=>` 未实现 vs 标准头不存在）、触发条件（源码实际使用 `<=>` vs
无条件 include 冗余头）、修复（可移植比较等价函数 vs 移除冗余 include /
`__has_include` 守卫）均不同，**非等价命中**，本条为其 similar_to 扩展。
其余 libc++ 相关正式条目（E191 链接缺失 / E247 std::__n1 符号 / E238
features.h / E306 std::polar）均为不同主题。无覆盖。

## 知识库沉淀价值

- 可复用问题类别：OHOS SDK 15 系 libc++ 缺失 C++20 标准头
  （`<source_location>` 为首个实例，后续 `<span>`/`<format>` 等同类风险同理）。
- 适用对象：一切目标 OHOS 且（无条件）引用 C++20 标准头的 C/C++ 库，
  尤其是"库本体有 `__has_include` 守卫但测试/示例/下游代码没有"的项目。
- 决策价值：一眼识别 `fatal error: '<C++20 头>' file not found` 并区分
  "真实使用"与"冗余 include"：零使用直接删 include（零行为变更）；真实使用
  则按 `__has_include` 守卫降级或替换为平台等价实现；避免误把"库能编译"
  当作"全套代码可编译"。

## 方案

1. 确认使用性：`grep -rn "std::source_location" <src>`，区分真实使用与冗余 include。
2. 冗余 include（0 使用）：直接删除该行（reflect-cpp 0.17.0 即此，10 文件
   各 -1 行，零行为变更）。
3. 真实使用：加 `#if __has_include(<source_location>)` 守卫 + 降级路径
   （如以空字符串/固定位置代替位置信息），保持与库本体一致的降级语义。
4. 配方层：补丁分类标注 `type: portability`、`platform_only: true`；
   `guard` 注明"OHOS SDK libc++ 缺该头；上游工具链升级至 libc++ 16+ 后
   include 可恢复"。

## 验证证据

- 修复前：`cmake --build` 97 目标中 10 个测试目标失败
  （`fatal error: 'source_location' file not found`，首错
  tests/json/test_extra_fields.cpp:22）。
- 修复后：`cmake --build` 97/97 OK；`ctest -j 20` **193/193 passed, 0 failed**
  （Total Test time 0.98s，本机 OHOS aarch64 实机执行）；
  `conan create`（ohos-aarch64 profile）exit 0，test_package 28 断言全过。

## 禁止做法

- 把"库本体编译通过"当作全代码树可编译的证据跳过测试/下游验证：
  `__has_include` 守卫会让本体静默降级而测试炸掉。
- 对真实使用点直接删 include 不降级：`std::source_location::current()`
  调用点会变成未声明标识符，只是把编译错误换个位置。
- 把该头缺失归因为"当前库缺陷"或"构建系统问题"：这是 OHOS SDK 15 系
  toolchain 的能力缺口，属平台可移植性补丁，不进基线/共享框架归因。
