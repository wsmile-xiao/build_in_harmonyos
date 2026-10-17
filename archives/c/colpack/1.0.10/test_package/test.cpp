// 消费者测试：真实调用 ColPack 图着色 API（Conan L1 test_package）。
// 内嵌上游 SampleDrivers 使用的 Graphs/mtx-spear-head.mtx（10 顶点 28 非零），
// 运行时写入临时文件，走 SRC_FILE 解析 → LARGEST_FIRST/DISTANCE_TWO 着色
// → GetVertexColors 取回颜色向量并做行为断言。
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

// ColPack 公共头不自包含：上游示例（SampleDrivers/Basic/*）均先包含
// ColPackHeaders.h（拉入 GraphColoring 基类、<list>/<map>/Timer 等声明），
// 之后再包含具体接口头。
#include <ColPack/ColPackHeaders.h>
#include <ColPack/GraphColoringInterface.h>

static const char *kMatrixMarket =
    "%%MatrixMarket matrix coordinate real general\n"
    "10 10 28\n"
    "1 1 .666666666666667\n"
    "1 2 -6.310289677458059e-7\n"
    "1 3 .283314888590275\n"
    "1 4 .27224066696528\n"
    "1 5 .666666666666667\n"
    "1 6 .27224066696528\n"
    "1 7 .666666666666667\n"
    "1 8 .27224066696528\n"
    "1 9 .666666666666667\n"
    "1 10 .27224066696528\n"
    "2 1 -6.310289677458059e-7\n"
    "2 2 .27224066696528\n"
    "3 1 .283314888590275\n"
    "3 3 .577703998805546\n"
    "4 1 .27224066696528\n"
    "4 4 .283314888590275\n"
    "5 1 .666666666666667\n"
    "5 5 .283314888590275\n"
    "6 1 .27224066696528\n"
    "6 6 .283314888590275\n"
    "7 1 .666666666666667\n"
    "7 7 .283314888590275\n"
    "8 1 .27224066696528\n"
    "8 8 .283314888590275\n"
    "9 1 .666666666666667\n"
    "9 9 .283314888590275\n"
    "10 1 .27224066696528\n"
    "10 10 .283314888590275\n";

int main() {
    // 1. 将内嵌矩阵写入运行时临时文件
    const char *path = "colpack_test_matrix.mtx";
    std::ofstream mtx(path);
    if (!mtx) {
        std::fprintf(stderr, "FAIL: cannot create %s\n", path);
        return 2;
    }
    mtx << kMatrixMarket;
    mtx.close();

    // 2. 真实 API：从 MatrixMarket 文件建图并做距离二着色
    ColPack::GraphColoringInterface graph(SRC_FILE, path, "AUTO_DETECTED");
    graph.Coloring("LARGEST_FIRST", "DISTANCE_TWO");

    // 3. 行为断言：取回颜色向量并校验
    std::vector<int> colors;
    graph.GetVertexColors(colors);
    if (colors.size() != 10u) {
        std::fprintf(stderr, "FAIL: expected 10 vertices, got %zu\n", colors.size());
        return 1;
    }
    for (size_t i = 0; i < colors.size(); ++i) {
        if (colors[i] < 0) {
            std::fprintf(stderr, "FAIL: vertex %zu has negative color %d\n", i, colors[i]);
            return 1;
        }
    }
    int max_color = 0;
    for (size_t i = 0; i < colors.size(); ++i) {
        if (colors[i] > max_color) {
            max_color = colors[i];
        }
    }
    if (max_color + 1 < 2) {
        std::fprintf(stderr, "FAIL: connected graph must need >= 2 colors, got %d\n", max_color + 1);
        return 1;
    }
    if (max_color + 1 > 10) {
        std::fprintf(stderr, "FAIL: 10-vertex graph cannot need more than 10 colors, got %d\n",
                     max_color + 1);
        return 1;
    }

    std::printf("ColPack DISTANCE_TWO coloring OK: %d colors for 10 vertices\n", max_color + 1);
    graph.PrintVertexColoringMetrics();
    return 0;
}
