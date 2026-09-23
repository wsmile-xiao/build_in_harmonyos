# DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms：OHOS clang15/libc++15 缺 C++20 std::ranges 算法重载

> Contributor: AtomCode/oh-executor | Status: Draft | Updated: 2026-09-02
> Source: ada 4.0.0 HarmonyOS PC adaptation（patches/0002 ranges_compat.h）
> 对应：knowledge/drafts/DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms.kv

## 现象

OHOS SDK clang 15.0.4（libc++，LLVM 15）下以 `-std=c++20` 编译 ada 4.0.0
（WHATWG URL 解析库），凡使用 `std::ranges` 算法的编译单元全部报错：

```text
no member named 'find_if' in namespace 'std::ranges'
no member named 'binary_search' in namespace 'std::ranges'
no member named 'lower_bound' in namespace 'std::ranges'
```

ada 3.3.0 已用 `ranges_compat.h` 减量 polyfill 解决 any_of/all_of/replace/
find_if/find_if_not/stable_sort；4.0.0 的 IDNA 实现新增对 `lower_bound`（含
投影 4 参形式）与 `binary_search` 的使用，需扩展 polyfill。上游 libc++ 的
std::ranges 算法随 C++20 标准库逐步落地，OHOS SDK 15 的 libc++ 未实现这些
重载，属 toolchain 能力缺口而非源码错误；经典迭代器算法在 OHOS libc++ 完整
可用，可安全委托。

## 根因

- OHOS libc++（LLVM 15）未实现 `std::ranges` 命名空间下的算法重载（含 range
  形式与投影形式）。
- `lower_bound` 的调用形态为 4 参 `(span, value, comp{}, proj)`，投影到
  range-high 元素；`binary_search` 假定已排序 range，须自行实现二分循环。

## 方案

新增 `include/ada/ranges_compat.h`，在 `namespace std::ranges` 内提供减量
实现：

- `any_of / all_of / replace / find_if / find_if_not / stable_sort`：仅委托
  `std::begin / std::end` 经典迭代器算法。
- `lower_bound(R&&, value, comp={}, proj={})`：二分循环 + `std::invoke(proj,*it)`
  比较，返回迭代器。
- `binary_search(R&&, value)`：二分循环，命中返回 true。

`common_defs.h` 在 `#include <version>` 后引入 `"ada/ranges_compat.h"`，
保证所有翻译单元在使用 `std::ranges` 前已包含 polyfill。

## 验证

- 命令：`clang++ -std=c++20 -stdlib=libc++ ...`（OHOS toolchain）
- 上游测试：`ctest --output-on-failure` → 317/317 passed（ada 4.0.0）
- 鸿蒙专项：`ohos_special_test` → ranges polyfill OK / ada url parse OK / ALL PASS
- 消费者验证：`conan create`（test_package 1/1）通过；本地 W3 本地 CI 模拟通过

## 与现有知识的关系（查重证据）

- E292（ctest/GTest 测试迁移）：该条目是大型 C++ 测试体系的环境分层迁移策略，
  与 libc++ 缺失 std::ranges 算法的编译期 polyfill 无关，仅在 match_keywords
  含泛化 "ranges" 字样；非同一错误模式。
- DRAFT-libcxx15-missing-cpp20-spaceship：同为 OHOS libc++15 缺 C++20 库能力
  的编译期缺口（operator<=>），但错误签名、受影响 API（容器比较 vs ranges
  算法）与修复方式（可移植等价 vs 迭代器委托 polyfill）均不同，属独立条目。
- index.tsv / graph / doc 均无针对 std::ranges 算法缺失的既有条目 → 新增。

## 适用边界

- 适配 clang15/libc++15 + C++20 的 OHOS 库，使用 std::ranges 算法重载时适用。
- 若上游已升级 toolchain 或源码可用经典迭代器替代，无需 polyfill。
- 注意 lower_bound 投影 4 参签名与 binary_search 的排序前提，勿机械照搬。
## 第二修复策略（调用点改写）：baloo 26.04.3 实证

> 2026-09-06 追加。第一策略（ada ranges_compat.h polyfill）之外，同一问题
> （OHOS libc++15 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 隐藏全部 std::ranges 算法）
> 在 baloo 上以第二种策略解决：**调用点改写**。

- 前提差异：baloo 只在 `src/engine/andpostingiterator.cpp` 与
  `src/engine/phraseanditerator.cpp` 两处用了 `std::ranges::any_of`，没有公共头
  注入面；为 polyfill 新增头文件并让所有 TU 包含的成本高于直接改写调用点。
- 做法（patch 0001 第 3 组）：

  ```cpp
  // before: std::ranges::any_of(m_iterators, [](const auto &e){ return e == nullptr; })
  // after:  C++11 可移植
  if (std::any_of(m_iterators.begin(), m_iterators.end(),
                  [](const auto &e) { return e == nullptr; })) {
      m_iterators.clear();
  }
  ```
  同时把 `#include <ranges>` 换成 `#include <algorithm>`。
- 触发时序证据：该 DRAFT 的 baloo 实例必须先把标准真提到 C++20（否则报的是
  `no member named 'ranges' in namespace 'std'`，见
  DRAFT-baloo-kf6-ohpcd-cmake-toolchain-cppstd 的 cppstd 时序坑）；到真 C++20 后
  才进入本 DRAFT 的报错 `no member named 'any_of' in namespace 'std::ranges'`
  （build4.log L451/L462）。
- 验证：build8/build9（authoritative CI）21/21 PASS，test_package 1/1。

### 策略对比

| 维度 | ada polyfill（第一策略） | baloo 调用点改写（第二策略） |
|------|--------------------------|------------------------------|
| 适用 | 调用点多、有公共头/`<version>` 注入点 | 调用点少（≤ 个位数）、无干净注入面 |
| 改动面 | 新增头 + 全部 TU 包含 | 仅改调用点 + include |
| 风险 | 注入时机/签名（投影 4 参）易错 | 逐点改写易漏（需全仓扫描 std::ranges） |
| 取舍 | 一次解决整库 | 轻量、可移植 C++11 |

两策略同属"DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms"一类，不另开 E 号。
