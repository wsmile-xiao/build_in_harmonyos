# boost1.84-graph

## 简介
Boost.Graph 1.84.0 组件包：图结构与图算法库（header-only 为主）+ Graphviz/GraphML 读写编译库。Debian 风格从 boost 1.84.0 拆分的独立组件包。

## OHOS 适配
- **构建系统**: b2 不兼容 OHOS（E068/E099），手动 clang++ 编译 `libs/graph/src/{read_graphviz_new,graphml}.cpp` → `libboost_graph.a`
- **头文件**: 完整 `boost/` 头文件树随包安装（graph 算法 header-only 全量可用）
- **补丁**: `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 宏旁路（OHOS musl 无该 API，R8 合规）
- **上游测试**: Jamfile 注册 120 目标（96 run + 24 compile）全量真实执行，120/120 通过

## 依赖
- 无 conan 依赖（boost_graph.a 的 regex 实现全部内联，llvm-nm 符号表实证；下游需独立 regex 时安装 boost/1.84.0 全量包——系统注记口径）

## 组件
| 组件 | CMake 目标 | 内容 |
|---|---|---|
| boost_headers | BoostGraph::headers | 完整 boost/ 头文件树 + 宏传播 |
| boost_graph | BoostGraph::graph | libboost_graph.a（read_graphviz/read_graphml/write_graphml） |
