# DRAFT-graaf-1.1.0-header-only-tpp-noninline-odr — header-only 库 .tpp 中非 inline 自由函数的重复符号

## 问题现象

graaf 1.1.0 适配中新增鸿蒙专项测试（`ohos_adaptation_test.cpp`，调用
`bron_kerbosch`）后，测试套件链接失败：

```
ld.lld: error: duplicate symbol:
  graaf::algorithm::detail::do_get_intersection(...)
ld.lld: error: duplicate symbol:
  graaf::algorithm::detail::set_union(...)
ld.lld: error: duplicate symbol:
  graaf::algorithm::detail::set_difference(...)
```

上游只有 `bron_kerbosch_test.cpp` 一个翻译单元包含该头，恰好不触发；第二个
包含该头的翻译单元出现后即暴露。

## 根因分析

`include/graaflib/algorithm/clique_detection/bron_kerbosch.tpp` 的 `detail`
命名空间定义了三个**非模板、非 inline** 的自由函数
（`do_get_intersection` / `set_union` / `set_difference`）。header-only 库的
`.tpp` 被多个翻译单元 `#include` 时，每个翻译单元都会为这些函数生成同名全局
符号，违反 ODR（单一定义规则），链接器报重复符号。这是 header-only 库实现
层面的隐患，与平台无关——标准库（libstdc++/libcxx）的迭代顺序或链接器差异只
决定何时被踩中。

## 解决方案

给三个函数加 `inline` 关键字：

```cpp
inline vertex_set_t do_get_intersection(const vertex_set_t& lhs,
                                        const vertex_set_t& rhs) {...}
inline vertex_set_t set_union(const vertex_set_t& lhs,
                              const vertex_set_t& rhs) {...}
inline vertex_set_t set_difference(const vertex_set_t& lhs,
                                   const vertex_set_t rhs) {...}
```

`inline` 使函数在 ODR 上允许跨翻译单元重复定义（弱符号合并），行为不变。

## 验证结果

修复后重新链接，完整套件 750/750 通过（746 上游 + 4 鸿蒙专项），其中
`OHOSAdaptation.BronKerboschUsesPatchedMaxElement` 验证了 bron_kerbosch
路径在修复后仍正确。

## 适用边界 / 反例

- 适用：所有在 `.tpp`/`.inc`（被 `.h` include）中定义非模板自由函数的
  header-only 库；多翻译单元包含时触发。修复方式：加 `inline`（推荐）、改为
  模板，或改用 `static`（不建议，每 TU 一份拷贝浪费且行为可能不一致）。
- 反例：函数是模板函数（模板天然满足 ODR）；或 .tpp 只被单个翻译单元包含
  （不触发，但仍是隐患，建议顺手修掉）。
