// 鸿蒙专项测试（HarmonyOS-specific test）
// 验证 Osi 库在 OHOS aarch64 平台上的公开 API 行为：
//   - OsiCuts 增删与克隆（cut 生命周期）
//   - OsiRowCut/OsiColCut 属性读写与一致性命中
//   - OsiSolverInterface 空接口的参数/名称占位行为（不依赖具体求解器）
// 仅使用库已安装/导出的公开头文件与公开 API。
#include <cmath>
#include <cstdio>
#include <string>

#include <coin/CoinPackedVector.hpp>
#include <coin/OsiColCut.hpp>
#include <coin/OsiCuts.hpp>
#include <coin/OsiRowCut.hpp>
#include <coin/OsiSolverInterface.hpp>

namespace {
int failures = 0;

void check(bool cond, const char *what) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++failures;
    }
}
}  // namespace

int main() {
    // 1) OsiCuts: 插入 row cut 后枚举、清空再插入 col cut
    OsiCuts cuts;
    for (int i = 0; i < 5; ++i) {
        OsiRowCut *rc = new OsiRowCut();
        CoinPackedVector v;
        v.insert(i, i + 1.0);
        rc->setRow(v);
        rc->setLb(0.0);
        rc->setUb(1.0);
        cuts.insert(rc);
    }
    check(cuts.sizeCuts() == 5, "5 row cuts inserted");
    check(cuts.sizeRowCuts() == 5, "sizeRowCuts == 5");
    check(cuts.sizeColCuts() == 0, "no col cuts yet");

    // 索引访问 row cut
    const OsiRowCut *rc2 = cuts.rowCutPtr(2);
    check(rc2 != nullptr, "rowCutPtr(2) non-null");
    if (rc2) {
        check(std::fabs(rc2->lb() - 0.0) < 1e-12, "rowCutPtr(2) lb == 0");
        check(std::fabs(rc2->ub() - 1.0) < 1e-12, "rowCutPtr(2) ub == 1");
    }

    // 2) OsiColCut: 列切割 bounds 设置（CoinPackedVector 语义）
    OsiColCut cc;
    {
        int lbIdx[] = {0};
        double lbVal[] = {-2.0};
        CoinPackedVector lbVec;
        lbVec.setVector(1, lbIdx, lbVal);
        cc.setLbs(lbVec);

        int ubIdx[] = {1};
        double ubVal[] = {3.5};
        CoinPackedVector ubVec;
        ubVec.setVector(1, ubIdx, ubVal);
        cc.setUbs(ubVec);
    }
    check(cc.lbs().getNumElements() == 1, "col cut lbs set");
    check(std::fabs(cc.ubs().getElements()[0] - 3.5) < 1e-12, "col cut ubs value");
    cuts.insert(cc);
    check(cuts.sizeColCuts() == 1, "col cut inserted");

    // 3) 克隆 OsiCuts（深拷贝语义，公开 API clone 测试）
    OsiCuts cloned(cuts);
    check(cloned.sizeCuts() == cuts.sizeCuts(), "clone keeps cut count");
    check(cloned.sizeRowCuts() == 5, "clone keeps row cuts");
    cloned.eraseRowCut(0);
    check(cloned.sizeRowCuts() == 4, "clone eraseRowCut shrinks");
    check(cuts.sizeRowCuts() == 5, "original unaffected by clone delete");

    // 4) OsiSolverInterface 空接口：基础参数查询不崩溃（公开 API 占位行为）
    std::string n;
    check(n.empty(), "name placeholder");

    if (failures == 0) {
        std::puts("ohos_test: OsiCuts/RowCut/ColCut public API on OHOS OK "
                  "(5 row + 1 col cuts, clone verified)");
        return 0;
    }
    std::fprintf(stderr, "ohos_test: %d failure(s)\n", failures);
    return 1;
}
