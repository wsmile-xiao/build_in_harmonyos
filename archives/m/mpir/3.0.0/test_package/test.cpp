#include <cstdio>
#include <mpirxx.h>

// 消费者测试：以库使用方身份真实调用 MPIR C++ 接口（R34）。
// 1) 多精度整数乘除回代；2) mpir_si 最小值混合除法/取模——这正是
//    0001 补丁修复的有符号溢出 UB 场景，作为鸿蒙适配回归用例；
// 3) 有理数运算。
static int failures = 0;

static void check(bool ok, const char *what)
{
    if (!ok)
    {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

int main()
{
    // 大整数乘法后回代：c/b==a 且 c%b==0
    mpz_class a("123456789012345678901234567890123456789");
    mpz_class b("987654321098765432109876543210987654");
    mpz_class c = a * b;
    check(c / b == a && c % b == 0, "mpz multiply/divide round-trip");

    // 阶乘
    mpz_class f = 1;
    for (unsigned i = 2; i <= 30; ++i)
        f *= i;
    check(f == mpz_class("265252859812191058636308480000000"), "30! value");

    // mpir_si LONG_MIN 参与混合运算（UB 修复回归）：SI_MIN / (-(SI_MIN)) == -1，余 0
    volatile mpir_si si_min = GMP_SI_MIN;
    mpz_class half = -mpz_class(static_cast<mpir_si>(GMP_SI_MIN));
    mpz_class q = si_min / half;
    mpz_class r = si_min % half;
    check(q == -1, "si_min / -si_min == -1");
    check(r == 0, "si_min % -si_min == 0");

    // 有理数加法
    mpq_class frac(3, 7);
    frac += mpq_class(2, 7);
    check(frac == mpq_class(5, 7), "mpq addition");

    // 浮点近似：sqrt(2) 精度区间（默认精度 ~64 比特）
    mpf_class two(2);
    mpf_class s = sqrt(two);
    check(s > mpf_class("1.4142") && s < mpf_class("1.4143"), "sqrt(2) bounds");

    if (failures)
    {
        std::printf("test_mpir: %d check(s) failed\n", failures);
        return 1;
    }
    std::printf("test_mpir: all checks passed\n");
    return 0;
}
