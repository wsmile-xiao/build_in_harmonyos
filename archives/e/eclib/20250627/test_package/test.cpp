/* 真实断言：用 eclib 跑 Tate 算法算两条经典椭圆曲线的导子。
 *
 *   11a1: [0,-1,1,-10,-20]  → N = 11
 *   37a1: [0, 0,1, -1,  0]  → N = 37
 *
 * Cremona 标号里的数字就是导子，属教科书事实，可独立核对。
 * 用法照上游 tests/conductor.cc：先 initprimes 建素数表，再 Curvedata → CurveRed → getconductor。
 */
#include <cstdio>
#include <eclib/curve.h>

static int check(const char *name, long a1, long a2, long a3, long a4, long a6, long expect)
{
    Curvedata CD(bigint(a1), bigint(a2), bigint(a3), bigint(a4), bigint(a6), 1);
    CurveRed CR(CD);
    bigint N = getconductor(CR);
    long got = I2long(N);
    if (got != expect) {
        std::printf("eclib: %s 的导子应为 %ld，实得 %ld\n", name, expect, got);
        return 1;
    }
    std::printf("eclib: %s 导子 N = %ld 通过\n", name, got);
    return 0;
}

int main()
{
    initprimes("PRIMES", 0);
    int bad = 0;
    bad += check("11a1", 0, -1, 1, -10, -20, 11);
    bad += check("37a1", 0, 0, 1, -1, 0, 37);
    return bad;
}
