/* 真实断言：GF(7) 上做加乘与求逆，结果可手算；另验 GMP 大整数（证明 gmpxx 真链上了）。
 * 注意 Modular 的特化按具体头文件提供：用总入口 <givaro/modular.h>（含 modular-floating 的 Modular<double> 特化），
 * 不能写 Modular<int64_t>（无该特化，实撞 implicit instantiation of undefined template）。 */
#include <cstdio>
#include <givaro/modular.h>
#include <givaro/givinteger.h>

int main() {
    Givaro::Modular<double> F(7);
    double a, b, c;
    F.init(a, 5); F.init(b, 4);
    F.add(c, a, b);                        /* 5+4 = 9 ≡ 2 (mod 7) */
    if (c != 2) { std::fprintf(stderr, "GF(7): 5+4 应为 2，实得 %g\n", c); return 1; }
    F.mul(c, a, b);                        /* 5*4 = 20 ≡ 6 (mod 7) */
    if (c != 6) { std::fprintf(stderr, "GF(7): 5*4 应为 6，实得 %g\n", c); return 1; }
    F.inv(c, a);                           /* 5*3 = 15 ≡ 1 → inv(5)=3 */
    if (c != 3) { std::fprintf(stderr, "GF(7): inv(5) 应为 3，实得 %g\n", c); return 1; }
    Givaro::Integer x("123456789012345678901234567890"), y(2), z;
    z = x * y;
    if (z != Givaro::Integer("246913578024691357802469135780")) {
        std::fprintf(stderr, "GMP 大整数乘法结果不符\n"); return 1;
    }
    std::printf("givaro: GF(7) 加/乘/逆 通过；GMP 大整数乘法 通过\n");
    return 0;
}
