# DRAFT-graaf-1.1.0-welsh-powell-deterministic-coloring — 贪心着色对无序容器迭代顺序的依赖修复

## 问题现象

graaf 1.1.0 上游测试套件在 OHOS 上运行，`WelshPowellTest/0.CompleteGraph`
（K4 完全图）失败：

```
[  FAILED  ] WelshPowellTest/0.CompleteGraph
Expected equality of these values:
  coloring          Which is: { (0, 1), (1, 1), (2, 1), (3, 0) }
  expected_coloring Which is: { (3, 0), (2, 1), (1, 2), (0, 3) }
```

`{ (0,1), (1,1), (2,1), (3,0) }` 中顶点 0/1/2 相邻却同色，是**无效着色**。

## 根因分析

上游 `welsh_powell_coloring` 的实现是：

```cpp
int color = 0;
for (const auto& neighbor : graph.get_neighbors(current_vertex)) {
  if (color_map.contains(neighbor) && color_map[neighbor] == color) {
    color++;
  }
}
color_map[current_vertex] = color;
```

该逻辑只在**邻居恰好按颜色升序被遍历**时才正确：候选色号 0 被占用 → 升到 1 →
但 1 是否被占用取决于遍历顺序，若占用色号 1 的邻居排在占用色号 0 的邻居之前，
第二次 `== color` 比较（此时 color 仍为 0 或已升）会漏检。`std::unordered_set`
迭代顺序与标准库实现相关——libstdc++ 与 libcxx-ohos（OHOS SDK llvm15）不同，
OHOS 下迭代顺序变化触发该缺陷，K4 的 4 顶点被着成 3 色且 0/1/2 同色。

## 解决方案

改为"收集已用色集合 + 取最小未用色"，结果与迭代顺序完全无关：

```cpp
std::unordered_set<int> used_colors;
for (const auto& neighbor : graph.get_neighbors(current_vertex)) {
  if (color_map.contains(neighbor)) {
    used_colors.insert(color_map[neighbor]);
  }
}
int color = 0;
while (used_colors.contains(color)) color++;
color_map[current_vertex] = color;
```

## 验证结果

- K4 完全图着色 `{3:0, 2:1, 1:2, 0:3}`（4 种颜色），与上游期望一致；
- 完整套件 750/750 通过（746 上游 + 4 鸿蒙专项）；
- 修复同时消除"相邻顶点同色"的潜在正确性缺陷，对任意迭代顺序均正确。

## 适用边界 / 反例

- 适用：任何"遍历已着色邻居、取首个未冲突色号"式贪心着色/调度实现。
- 反例：若算法明确按某种排序（如按度数降序且度数相同按 ID）遍历，则结果是
  确定的，不受容器迭代顺序影响，无需修改；本修复针对的是"依赖邻居容器迭代
  顺序"的写法。
