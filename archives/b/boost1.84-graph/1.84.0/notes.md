# boost1.84-graph 1.84.0 适配笔记

## 概述

Boost.Graph 组件独立打包（Debian 风格拆分形态），从 boost 1.84.0 官方源码
（sourceforge 归档，sha256 `a5800f4...`）裁剪编译。Boost b2 构建系统在
OHOS 不兼容（E068/E099：SHELL 执行机制失败），沿用 boost1.84 系六组件全绿
先例（system #8468 / chrono #8481 / random #8482 / thread #8554 /
math #8441）与 `archives/b/boost/1.84.0` 底稿的手动 clang++ 编译方案。

## 编译范围（与 libs/graph/build/Jamfile.v2 逐项核对）

`boost_graph` 编译目标只包含 2 个源文件（libs/graph/src 全集）：

| 源文件 | 内容 | 依赖 |
|---|---|---|
| `read_graphviz_new.cpp` | Graphviz DOT 解析器 | boost::regex（**全部内联**，见下） |
| `graphml.cpp` | GraphML XML 读写 | property_tree（header-only） |

其余 Boost.Graph 功能（adjacency_list / 全部图算法 / 属性映射 / VF2 同构 /
平面性 / 最大流等）均为 header-only，随完整 `boost/` 头文件树安装。

## regex 系统注记口径（关键设计决策）

`read_graphviz_new.cpp` `#include <boost/regex.hpp>` 且 Jamfile 声明
`<library>../../regex/build//boost_regex`，但：

1. `llvm-nm -u libboost_graph.a` 验证：**无任何 `boost::regex` 未定义符号**
   ——所用 regex 模板实现全部内联进目标文件（212 个 re_detail 符号已在 .o 内）；
2. 不链接 `-lboost_regex` 直接编译消费者程序 → 链接通过、`read_graphviz`
   正确解析 DOT（本地实测：`digraph G { a -> b; }` → 2v/1e）；
3. `graphviz.hpp` 头文件（write_graphviz 路径）用的是 `boost::xpressive`
   （header-only），同样无编译库依赖。

因此本包 **无 conan requires**（同 chrono/math/random 组件口径）。下游如需
独立使用 `boost::regex`（如 `#include <boost/regex.hpp>` 调 `regex_match`），
安装 `boost/1.84.0` 全量包（内含 `libboost_regex.a`）——即"regex 系统注记
口径"。`boost1.84-regex` 独立组件包制品仓暂无发布。

## 补丁（与同系组件一致）

`patches/0001-ohos-pthread-cancel-fix.patch`：`boost/core/detail/
sp_thread_sleep.hpp` 增加 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 宏旁路
（OHOS musl 无 `pthread_setcancelstate`），R8 合规（feature-detection 宏，
非平台宏），通过 `package_info.defines` 传播给所有下游。

## 上游测试（rule4：N = 上游注册数实测）

`libs/graph/test/Jamfile.v2` 注册 **120 个测试目标**（96 run + 24 compile），
本适配全部真实执行（**0 豁免**）：

- **96 run 型**：编译链接后真实运行，rc=0 判通过。含：
  - `graph.cpp` × 9（TEST=1..9 变体目标，`-DTEST=N` 逐一编译）
  - 3 个 timer 依赖（transitive_closure_test / dijkstra_heap_performance
    10000 / metric_tsp_approx metric_tsp_approx.graph）
  - 2 个 regex 依赖（graphviz_test --log_level=all / cycle_ratio_tests
    cycle_ratio_s382.90.dot）
  - 1 个 serialization 依赖（serialize.cpp，XML archive 往返）
  - 2 个 filesystem 依赖（all_planar_input_files_test / parallel_edges_
    loops_test，planar_input_graphs 目录）
  - metis_test（weighted_graph.gr）、mas_test/stoer_wagner_test（TEST_DIR）、
    random_matching_test（1000 1020）、graphml_test（graphml_test.xml 绝对
    路径——相对路径 cwd 不一致时 ptree 报 read error，实测确认需绝对路径）
- **24 compile 型**（b2 compile 语义：只编译不链接，含 property_iter.cpp
  × 9 变体）：编译 rc=0 判通过。注意 `reverse_graph_cc.cpp` 按上游语义为
  compile 型——链接期 `get_property(reverse_graph...)` 符号未定义是上游
  graph_name 属性模板特化缺失，b2 compile 不链接故上游也"通过"，本适配
  严格按 compile 语义执行（只编译）。

测试期辅助库（timer/regex/serialization/filesystem）从同一源码树按各库
Jamfile 源清单现场编译（`_build_test_helper_libs`），**仅用于测试链接，
不入包**——保持配方自包含（W0 无 conan requires，CI 无需预拉依赖）。

filesystem 源码需 `-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF`（clang 15 +
c++17 无 std::atomic_ref，与 boost/1.84.0 底稿口径一致）。

**实测结果：120/120 通过（100%）**。

## 本地实测环境备忘

- 工具链：`/data/service/hnp/bin/clang++`（clang 15，libc++）
- 运行时：`LD_LIBRARY_PATH=$(dirname $(clang++ -print-file-name=libc++_shared.so))`
- 首次探测发现：graphml_test 传相对路径报 `xml_parser_error: read error`
  （ptree 从 istream 读文件名时 cwd 依赖），传绝对路径通过——配方内测试
  统一用 `<testdir>` 前缀替换为绝对路径。

## 踩坑与决策记录

1. **b2 绕过**（E068/E099）：直接 clang++ 手动编译，同系全部组件先例。
2. **regex 不打包理由**：符号表实证 + 链接实证（probe_link.cpp 不链
   boost_regex 通过），且 graph 的 Jamfile regex 依赖仅服务于源文件内部的
   tokenizer 实现（已内联）。若下游要跑上游 graphviz_test.cpp 全量测试，
   需要 boost_regex（已在测试辅助库中现场编译覆盖，本包测试已含该路径）。
3. **property_tree 无需打包**：header-only，graphml.cpp 直接可用。
4. **版本号**：首次适配上游 1.84.0 → `1.84.0`（R37）。
