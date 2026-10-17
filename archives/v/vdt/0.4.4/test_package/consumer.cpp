// vdt 0.4.4 消费者验证用例
//
// 仅使用 vdt 库公开头文件与公开 API（vdt::fast_exp/vdt::fast_sin/vdt::expv
// 等），编译链接 libvdt.so 并运行，对拍 vdt 结果与标准库参考值，验证第三方
// 业务组件在 HarmonyOS aarch64 上可以正常调用 vdt。
#include <vdt/vdtMath.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

// 相对误差阈值：vdt 为快速近似实现，双精度函数对拍允许 1e-7 相对偏差。
static int g_fail = 0;

static void check(double got, double want, const char *name) {
    // 分母取绝对值：want<0 时若直接用带符号 want，比值会变负，
    // `rel > 1e-7` 恒为 false，断言会被静默绕过（相对误差必须恒为非负）。
    double rel = std::fabs((got - want) / (want != 0.0 ? std::fabs(want) : 1.0));
    if (rel > 1e-7 || !std::isfinite(got)) {
        std::printf("FAIL %s: got=%.17g want=%.17g rel=%.3e\n", name, got, want, rel);
        g_fail = 1;
    } else {
        std::printf("OK   %s: got=%.17g (rel=%.3e)\n", name, got, rel);
    }
}

int main() {
    // 标量双精度签名：T(T)（vdt 公开 API 为 fast_* 命名）
    check(vdt::fast_exp(1.0), std::exp(1.0), "vdt::fast_exp(1.0)");
    check(vdt::fast_sin(0.5), std::sin(0.5), "vdt::fast_sin(0.5)");
    check(vdt::fast_cos(0.5), std::cos(0.5), "vdt::fast_cos(0.5)");
    check(vdt::fast_log(2.0), std::log(2.0), "vdt::fast_log(2.0)");
    check(vdt::fast_isqrt(2.0), 1.0 / std::sqrt(2.0), "vdt::fast_isqrt(2.0)");

    // 数组签名：void(unsigned int, const T*, T*)（对外导出符号）
    const unsigned int n = 4;
    const double in[n] = {0.1, 0.5, 1.0, 2.0};
    double out[n];
    vdt::expv(n, in, out);
    for (unsigned int i = 0; i < n; ++i) {
        char nm[64];
        std::snprintf(nm, sizeof nm, "vdt::expv[%u]", i);
        check(out[i], std::exp(in[i]), nm);
    }
    vdt::sinv(n, in, out);
    for (unsigned int i = 0; i < n; ++i) {
        char nm[64];
        std::snprintf(nm, sizeof nm, "vdt::sinv[%u]", i);
        check(out[i], std::sin(in[i]), nm);
    }

    std::printf("vdt consumer probe: %s\n", g_fail ? "FAILED" : "PASSED");
    return g_fail;
}
