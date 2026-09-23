// test_package — Conan L1 测试（消费者视角，仅使用 osi 已安装/导出的公开 API）
// 验证 OsiRowCut / OsiCuts / CoinPackedVector 的公开接口可编译、链接并正确运行。
#include <cmath>
#include <cstdio>
#include <vector>

#include <coin/CoinPackedVector.hpp>
#include <coin/OsiCuts.hpp>
#include <coin/OsiRowCut.hpp>

int main() {
    int failures = 0;

    // OsiRowCut 公开 API：设置行向量与上下界
    OsiRowCut cut;
    CoinPackedVector row;
    int indices[] = {1, 3, 5};
    double values[] = {2.0, -1.0, 0.5};

    row.setVector(3, indices, values);
    cut.setRow(row);
    cut.setLb(-1.0);
    cut.setUb(4.0);

    if (cut.row().getNumElements() != 3) {
        std::fprintf(stderr, "FAIL: row element count\n");
        ++failures;
    }
    if (cut.row().getIndices()[0] != 1 || cut.row().getIndices()[2] != 5) {
        std::fprintf(stderr, "FAIL: row indices\n");
        ++failures;
    }
    if (std::fabs(cut.row().getElements()[0] - 2.0) >= 1e-12 ||
        std::fabs(cut.row().getElements()[1] + 1.0) >= 1e-12) {
        std::fprintf(stderr, "FAIL: row values\n");
        ++failures;
    }
    if (std::fabs(cut.lb() + 1.0) >= 1e-12 || std::fabs(cut.ub() - 4.0) >= 1e-12) {
        std::fprintf(stderr, "FAIL: cut bounds\n");
        ++failures;
    }

    // OsiCuts 公开 API：添加与枚举切割
    OsiCuts cuts;
    for (int i = 0; i < 3; ++i) {
        OsiRowCut *c = new OsiRowCut();
        c->setLb(-100.0);
        c->setUb(100.0);
        cuts.insert(c);
    }
    if (cuts.sizeCuts() != 3) {
        std::fprintf(stderr, "FAIL: cuts count\n");
        ++failures;
    }
    const OsiRowCut *first = cuts.rowCutPtr(0);
    if (first == nullptr || std::fabs(first->lb() + 100.0) >= 1e-12) {
        std::fprintf(stderr, "FAIL: first cut lookup\n");
        ++failures;
    }

    if (failures == 0) {
        std::puts("test_osi: OsiRowCut/OsiCuts public API OK (3 cuts inserted)");
        return 0;
    }
    std::fprintf(stderr, "test_osi: %d failure(s)\n", failures);
    return 1;
}
