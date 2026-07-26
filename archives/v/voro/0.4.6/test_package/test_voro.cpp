// test_voro.cpp — voro++ 消费者测试
// 验证 voro++ 库的 Voronoi 泰森多边形计算功能
// 测试 voronoicell 类和 container 类的核心 API
// API 用法参考上游示例 examples/basic/single_cell.cc、random_points.cc
#include "voro++.hh"
#include <cstdio>
#include <cmath>

int main() {
    // 测试1: 创建 voronoicell 并验证初始状态
    voro::voronoicell v;
    v.init(-1, 1, -1, 1, -1, 1);
    if (v.number_of_faces() != 6) {
        std::printf("FAIL: initial cell should have 6 faces, got %d\n", v.number_of_faces());
        return 1;
    }

    // 测试2: 计算单元体积（立方体边长 2，体积应为 8）
    double vol = v.volume();
    if (vol <= 0.0 || std::fabs(vol - 8.0) > 0.001) {
        std::printf("FAIL: cube volume expected ~8.0, got %f\n", vol);
        return 1;
    }

    // 测试3: 验证立方体边数（立方体有 12 条边）
    if (v.number_of_edges() != 12) {
        std::printf("FAIL: cube should have exactly 12 edges, got %d\n", v.number_of_edges());
        return 1;
    }

    // 测试4: 创建容器、添加粒子并验证总体积为正
    // 参考上游 examples/basic/random_points.cc 的用法
    voro::container con(-1, 1, -1, 1, -1, 1, 6, 6, 6, false, false, false, 8);
    con.put(0, 0.0, 0.0, 0.0);
    con.put(1, 0.5, 0.5, 0.5);
    con.put(2, -0.5, -0.5, -0.5);
    double total_volume = con.sum_cell_volumes();
    if (total_volume <= 0.0) {
        std::printf("FAIL: container total volume must be positive, got %f\n", total_volume);
        return 1;
    }

    // 测试5: 容器总体积应接近容器体积 8.0
    if (std::fabs(total_volume - 8.0) > 0.1) {
        std::printf("FAIL: container total volume expected ~8.0, got %f\n", total_volume);
        return 1;
    }

    std::printf("PASS: all voro++ tests passed\n");
    return 0;
}
