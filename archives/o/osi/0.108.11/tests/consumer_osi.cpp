// 消费者用例（consumer verification）
// 模拟业务上层组件/应用：仅通过 osi 已安装/导出的公开头文件、公开 API、
// 正常链接目标与运行时产物使用该三方库。
// 业务场景：线性规划分支切割求解器中常见的"切割池"组件——上层应用创建
// 行切割并维护一个切割池（OsiCuts），最终把池中切割数量与总非零元素数
// 作为可观察结果输出。此场景不依赖任何具体求解器，仅使用 libOsi 公开 API。
#include <cstdio>

#include <coin/CoinPackedVector.hpp>
#include <coin/OsiCuts.hpp>
#include <coin/OsiRowCut.hpp>

// 业务组件：CutPool —— 上层应用自实现的切割池
class CutPool {
public:
    explicit CutPool(double ub) : ub_(ub) {}
    void addRowCut(const int *idx, const double *val, int len, double lb) {
        OsiRowCut *rc = new OsiRowCut();
        CoinPackedVector v;
        v.setVector(len, idx, val);
        rc->setRow(v);
        rc->setLb(lb);
        rc->setUb(ub_);
        pool_.insert(rc);
        nonzero_ += len;
    }
    int size() const { return pool_.sizeRowCuts(); }
    int nonzeros() const { return nonzero_; }
    double ub() const { return ub_; }

private:
    OsiCuts pool_;
    double ub_;
    int nonzero_ = 0;
};

int main() {
    CutPool pool(1.0e30);  // 业务上层：切割池上界设为正无穷

    int idx0[] = {0, 1};
    double val0[] = {1.0, 1.0};
    pool.addRowCut(idx0, val0, 2, 1.0);

    int idx1[] = {1, 2, 3};
    double val1[] = {-1.0, 2.0, 0.5};
    pool.addRowCut(idx1, val1, 3, -5.0);

    int idx2[] = {4};
    double val2[] = {3.0};
    pool.addRowCut(idx2, val2, 1, 0.0);

    // 可观察业务结果：池中切割数、总非零元素数
    std::printf("CutPool: %d cuts, %d nonzero elements, ub=%.1e\n",
                pool.size(), pool.nonzeros(), pool.ub());

    if (pool.size() == 3 && pool.nonzeros() == 6) {
        std::puts("consumer_osi: CutPool via OsiCuts/OsiRowCut public API OK");
        return 0;
    }
    std::fprintf(stderr, "consumer_osi: unexpected pool state (cuts=%d nonzero=%d)\n",
                 pool.size(), pool.nonzeros());
    return 1;
}
