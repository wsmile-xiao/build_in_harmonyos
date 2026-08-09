// test_package smoke test — 实质调用 ADOL-C 公开 API (R34)
//
// 场景：对 f(x)=x*x 记录 tape，用 gradient() 求导并断言 dy/dx=2x。
// 覆盖 ADOL-C 核心机制：adouble 类型、trace_on/trace_off、gradient 驱动。
#include <adolc/adolc.h>
#include <cstdio>
#include <cmath>

int main() {
    adouble x, y;
    double xp = 2.0;   // 记录点
    double yp = 0.0;

    trace_on(1);
    x <<= xp;
    y = x * x;          // f(x) = x^2，解析导数为 2x
    y >>= yp;
    trace_off();

    double g[1] = {0.0};
    gradient(1, 1, &xp, g);   // 一维梯度：dy/dx

    double expected = 2.0 * xp;  // = 4.0
    bool ok = std::fabs(g[0] - expected) < 1e-9;
    printf("adolc gradient test: f(x)=x^2 at x=%.1f, dy/dx = %.6f (expect %.1f) -> %s\n",
           xp, g[0], expected, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
