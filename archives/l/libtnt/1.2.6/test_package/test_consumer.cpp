// test_consumer.cpp — libtnt 1.2.6 消费者用例
//
// 模拟真实数值应用消费 TNT 的场景（区别于 test_libtnt 的组件冒烟）：
//   场景 1：两态马尔可夫链稳态分布——行向量幂迭代 v ← v·P（matmult），
//           收敛后与解析稳态 π = (2/3, 1/3) 对比（PageRank 式用法）
//   场景 2：加权平均——Array1D 逐元素乘（形状一致的 operator* 正确
//           语义）+ 衰减指针求和，验证组合评分计算
// 全程 Stopwatch 计时（TNT 自带工具），断言 6 项，退出码判定。
#include <cmath>
#include <iostream>

#include <tnt.h>

static int g_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::cerr << "CHECK FAILED @" << __LINE__ << ": " #cond "\n";    \
            ++g_failures;                                                    \
        }                                                                    \
    } while (0)

static bool near_to(double a, double b, double eps) {
    return std::fabs(a - b) < eps;
}

int main() {
    // ── 场景 1：马尔可夫链稳态分布（幂迭代）──
    // 行随机转移矩阵 P = [0.9 0.1; 0.2 0.8]（每行和为 1，分布迭代
    // 保归一），解析稳态 π 满足 π = πP：
    // π0 = 0.9π0 + 0.2π1 → 0.1π0 = 0.2π1 → π0 = 2π1 → π = (2/3, 1/3)
    TNT::Array2D<double> P(2, 2);
    P[0][0] = 0.9; P[0][1] = 0.1;
    P[1][0] = 0.2; P[1][1] = 0.8;

    TNT::Array2D<double> v(1, 2);   // 行向量概率分布
    v[0][0] = 1.0; v[0][1] = 0.0;

    TNT::Stopwatch sw;
    sw.start();
    for (int it = 0; it < 200; ++it) {
        v = TNT::matmult(v, P);     // v_{k+1} = v_k · P
    }
    double elapsed = sw.stop();     // 200 次迭代耗时（Stopwatch 真实用途）

    CHECK(v.dim1() == 1 && v.dim2() == 2);
    CHECK(near_to(v[0][0], 2.0 / 3.0, 1e-9));   // 误差 0.7^k 几何衰减
    CHECK(near_to(v[0][1], 1.0 / 3.0, 1e-9));
    CHECK(near_to(v[0][0] + v[0][1], 1.0, 1e-12));  // 分布归一性保持
    CHECK(elapsed >= 0.0);

    // ── 场景 2：加权平均（Array1D 逐元素乘 + 衰减求和）──
    // 组合评分：权重 w 与得分 s 的加权平均 Σw_i·s_i / Σw_i
    TNT::Array1D<double> w(3);
    w[0] = 0.2; w[1] = 0.3; w[2] = 0.5;
    TNT::Array1D<double> s(3);
    s[0] = 80.0; s[1] = 90.0; s[2] = 100.0;

    TNT::Array1D<double> ws = w * s;   // 逐元素乘（同形状，正确语义）
    const double* raw = ws;            // operator const T*() 衰减
    double num = 0.0, den = 0.0;
    for (int i = 0; i < 3; ++i) {
        num += raw[i];
        den += w[i];
    }
    CHECK(near_to(num / den, 93.0, 1e-12));  // (16+27+50)/1.0 = 93

    if (g_failures != 0) {
        std::cerr << "libtnt consumer: " << g_failures << " check(s) FAILED" << std::endl;
        return 1;
    }
    std::cout << "libtnt consumer: all 6 checks passed (Markov steady state + weighted mean)" << std::endl;
    return 0;
}
