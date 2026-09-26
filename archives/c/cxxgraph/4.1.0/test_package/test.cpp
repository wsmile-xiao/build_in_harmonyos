// cxxgraph 4.1.0 — test_package 消费者验证
// 通过 Conan 包消费 CXXGraph 公开头文件与公开 API（非空壳测试）：
// 构建一个有向加权图，运行 Dijkstra 最短路径，验证业务可观察结果。
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

#include "CXXGraph/CXXGraph.hpp"
#include "CXXGraph/CXXGraphConfig.h"

template <typename T>
using shared = std::shared_ptr<T>;

int main()
{
    // 公开 API：创建节点（userId 为 string，data 为 int）
    CXXGraph::Node<int> n0("0", 0);
    CXXGraph::Node<int> n1("1", 1);
    CXXGraph::Node<int> n2("2", 2);
    CXXGraph::Node<int> n3("3", 3);

    // 公开 API：创建带权有向边（id, node1, node2, weight）
    auto e01 = std::make_shared<CXXGraph::DirectedWeightedEdge<int>>(0, n0, n1, 1.0);
    auto e12 = std::make_shared<CXXGraph::DirectedWeightedEdge<int>>(1, n1, n2, 2.0);
    auto e03 = std::make_shared<CXXGraph::DirectedWeightedEdge<int>>(2, n0, n3, 10.0);
    auto e32 = std::make_shared<CXXGraph::DirectedWeightedEdge<int>>(3, n3, n2, 2.0);

    // 公开 API：构图
    CXXGraph::Graph<int> g;
    g.addEdge(e01);
    g.addEdge(e12);
    g.addEdge(e03);
    g.addEdge(e32);

    // 公开 API：Dijkstra 最短路径（0 -> 2 最短路径为 0-1-2 = 3，非直连 0-3-2 = 12）
    const CXXGraph::DijkstraResult res = g.dijkstra(n0, n2);
    if (!res.success) {
        std::printf("FAIL: dijkstra not successful (%s)\n", res.errorMessage.c_str());
        return 1;
    }
    if (res.result != 3.0) {
        std::printf("FAIL: dijkstra distance=%f expected=3.0\n", res.result);
        return 1;
    }
    if (res.path.empty() || res.path.front() != "0") {
        std::printf("FAIL: dijkstra path missing source node\n");
        return 1;
    }

    std::printf("test_package cxxgraph: ALL PASSED (dijkstra 0->2 = %f, "
                "version %d.%d.%d)\n",
                res.result,
                (int)CXXGraph_VERSION_MAJOR,
                (int)CXXGraph_VERSION_MINOR,
                (int)CXXGraph_VERSION_PATCH);
    return 0;
}
