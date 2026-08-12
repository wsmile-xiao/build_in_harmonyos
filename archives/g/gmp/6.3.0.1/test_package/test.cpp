/* 真实断言：C 与 C++ 两套接口都要能用 —— 本变体存在的理由就是 --enable-cxx。 */
#include <cstdio>
#include <gmp.h>
#include <gmpxx.h>

int main() {
    /* C 接口：2^100 的十进制位数是 31（可查证） */
    mpz_t z; mpz_init(z); mpz_ui_pow_ui(z, 2, 100);
    size_t digits = mpz_sizeinbase(z, 10);
    if (digits != 31) { std::fprintf(stderr, "2^100 位数应为 31，实得 %zu\n", digits); return 1; }
    mpz_clear(z);

    /* C++ 接口（gmpxx）：没有 --enable-cxx 这段根本编不过 */
    mpz_class a("123456789012345678901234567890"), b(2);
    mpz_class c = a * b;
    if (c != mpz_class("246913578024691357802469135780")) {
        std::fprintf(stderr, "gmpxx 大整数乘法结果不符\n"); return 1;
    }
    /* 有理数：1/3 + 1/6 == 1/2 */
    mpq_class p(1, 3), q(1, 6), r = p + q;
    r.canonicalize();
    if (r != mpq_class(1, 2)) { std::fprintf(stderr, "1/3+1/6 应为 1/2\n"); return 1; }
    std::printf("gmp: C 接口 2^100 位数=31 通过；gmpxx 大整数与有理数 通过\n");
    return 0;
}
