/* 真实断言：用 lcalc 算 Riemann zeta 在 s=2 与 s=4 的值，对上闭式解。
 *
 *   ζ(2) = π²/6  ≈ 1.6449340668482264
 *   ζ(4) = π⁴/90 ≈ 1.0823232337111382
 *
 * 这两个是欧拉给出的闭式，误差容限取 1e-6（lcalc 默认精度远好于此）。
 * 用法照上游 doc/examples/example.cc：**必须先 initialize_globals()**，
 * 默认构造的 L_function<int> 就是 zeta。
 */
#include <cmath>
#include <cstdio>
#include <lcalc/L.h>

static int check(const char *name, Complex got, double expect)
{
    double re = real(got), im = imag(got);
    if (std::fabs(re - expect) > 1e-6 || std::fabs(im) > 1e-6) {
        std::printf("lcalc: %s 应为 %.10f，实得 %.10f%+.10fi\n", name, expect, re, im);
        return 1;
    }
    std::printf("lcalc: %s = %.10f 通过\n", name, re);
    return 0;
}

int main()
{
    initialize_globals();
    L_function<int> zeta;
    int bad = 0;
    bad += check("zeta(2)", zeta.value(Complex(2, 0)), M_PI * M_PI / 6.0);
    bad += check("zeta(4)", zeta.value(Complex(4, 0)), M_PI * M_PI * M_PI * M_PI / 90.0);
    return bad;
}
