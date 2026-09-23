# graaf

A light-weight C++20 graph library by bobluppes.

- 上游: https://github.com/bobluppes/graaf
- 类型: header-only（CMake INTERFACE，`#include <graaflib/...>`）
- 语言: C++20（concepts / requires）
- 适配版本: 1.1.0

## 功能

- directed / undirected / weighted graph 模板（`graaf::graph<V, E, graph_type>`）
- 算法：BFS/DFS 遍历、Dijkstra/Bellman-Ford/A*/Floyd-Warshall 最短路、Prim/Kruskal 最小生成树、Welsh-Powell/贪心着色、Bron-Kerbosch 极大团、Kosaraju/Tarjan 强连通分量、拓扑排序
- DOT 图输出、顶点属性工具

## OHOS 适配要点（1.1.0）

1. OHOS libc++（libcxx-ohos, llvm15）未实现 C++20 std::ranges 算法层
   （max_element/min_element/count_if）→ 等价替换为 std:: 算法 + begin()/end()。
2. Welsh-Powell 贪心着色改为确定性最小未用色分配（与无序容器迭代顺序无关，
   消除相邻顶点同色隐患）。
3. header-only .tpp 中非模板自由函数标 inline（多翻译单元包含时避免 ODR
   重复符号）。

## 测试

- 上游 GoogleTest 套件：750/750 通过（746 上游 + 4 鸿蒙专项 OHOSAdaptation）
- test_package 消费者验证：BFS/MST/着色正常

知识：见 knowledge/drafts/DRAFT-graaf-1.1.0-* 三对草稿。
