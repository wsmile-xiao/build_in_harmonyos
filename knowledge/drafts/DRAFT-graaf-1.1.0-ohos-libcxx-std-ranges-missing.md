# DRAFT-graaf-1.1.0-ohos-libcxx-std-ranges-missing — OHOS libc++ 缺少 C++20 std::ranges 算法的等价替换

## 问题现象

graaf 1.1.0（bobluppes/graaf，header-only C++20 图库）在 OHOS armv8
（clang 15 + libcxx-ohos）上编译测试套件时，三处源码报同一类错误：

```
include/graaflib/algorithm/clique_detection/bron_kerbosch.tpp:62:30:
  error: no member named 'max_element' in namespace 'std::ranges';
  did you mean 'std::max_element'?
include/graaflib/algorithm/minimum_spanning_tree/prim.tpp:50:30:
  error: no member named 'min_element' in namespace 'std::ranges'
include/graaflib/properties/vertex_properties.tpp:35:30:
  error: no member named 'count_if' in namespace 'std::ranges'
```

## 根因分析

OHOS PC SDK 自带的 libcxx-ohos（llvm 15 基线）没有实现 `<ranges>` 的算法层：
`std::ranges::max_element`、`min_element`、`count_if` 等均不存在，只有概念与
范围基础件。上游库使用 C++20 ranges 算法在 Linux/标准 libc++ 上编译正常，
在 OHOS 工具链上直接编译失败。属于工具链能力缺口，与 E130（libcxx-ohos 缺
`nullptr_t`/`__abi_tag__`）同源不同面，但与 E292（Arrow 的测试数据分层迁移，
只是关键词里恰好含 ranges）无关。

## 解决方案

把三处 `std::ranges::` 调用等价替换为 `std::` 算法 + 显式 `begin()/end()`，
带 projection 的改写为显式比较 lambda：

```cpp
// 原: *std::ranges::max_element(union_set, {}, [&graph](vertex_id_t id){ return graph.get_neighbors(id).size(); })
// 改:
const auto pivot_vertex = *std::max_element(
    union_set.begin(), union_set.end(),
    [&graph](vertex_id_t lhs, vertex_id_t rhs) {
      return graph.get_neighbors(lhs).size() <
             graph.get_neighbors(rhs).size();
    });

// 原: *std::ranges::min_element(candidates, comp)
// 改: *std::min_element(candidates.begin(), candidates.end(), comp)

// 原: std::ranges::count_if(graph.get_vertices(), pred)
// 改: std::count_if(graph.get_vertices().begin(), graph.get_vertices().end(), pred)
```

语义等价说明：`ranges::max_element(range, {}, proj)` 选取首个投影值最大元素，
等价于 `std::max_element(begin, end, comp)`（comp 比较投影值）；`count_if`
同理。`std::unordered_set` 迭代器满足前向迭代器要求，可安全使用。

## 验证结果

替换后完整重建 graaf 测试套件（GoogleTest，25 个上游测试源 + 鸿蒙专项）：

```
[==========] 750 tests from 210 test suites ran.
[  PASSED  ] 750 tests.
```

750/750 全部通过（746 上游 + 4 鸿蒙专项 OHOSAdaptation），行为与上游一致。

## 适用边界 / 反例

- 适用：任何在 OHOS 上编译、使用 std::ranges 算法的库；替换后需重跑测试。
- 反例：若调用的是 ranges 视图组合管道（`| std::views::filter ...`），不能简单
  替换为 std:: 算法，需按视图语义重构；本条目只覆盖单算法调用形态。
- 若后续 OHOS SDK 升级 libcxx-ohos 补全 ranges 算法，本替换仍然语义等价，
  无回归风险。
