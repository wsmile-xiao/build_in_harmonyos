/* 真实断言：用 BRiAl 在布尔多项式环里验两条可手算的恒等式。
 *
 * 布尔环 GF(2)[x0..xn]/(xi^2 - xi) 里 x*x = x，于是
 *   ① (x + y)^2 = x^2 + 2xy + y^2 = x + 0 + y = x + y      —— 平方等于自身
 *   ② deg(x*y*z) = 3                                        —— 乘积的次数
 *
 * 这两条都只有「库真的在做布尔多项式运算」时才成立：若 x*x 退化成普通多项式，
 * ① 立刻不等。比 dlopen 探针硬得多。
 */
#include <iostream>
#include <polybori.h>

using namespace polybori;

int main()
{
    BoolePolyRing ring(3);
    BooleVariable x(0, ring), y(1, ring), z(2, ring);

    BoolePolynomial p = x + y;
    BoolePolynomial sq = p * p;
    int bad = 0;

    if (!(sq == p)) {
        std::cerr << "brial: (x+y)^2 应等于 x+y，实得 " << sq << std::endl;
        bad = 1;
    } else {
        std::cout << "brial: (x+y)^2 == x+y 通过（" << sq << "）" << std::endl;
    }

    BoolePolynomial m = x * y * z;
    if (m.deg() != 3) {
        std::cerr << "brial: deg(x*y*z) 应为 3，实得 " << m.deg() << std::endl;
        bad = 1;
    } else {
        std::cout << "brial: deg(x*y*z) = 3 通过" << std::endl;
    }

    return bad;
}
