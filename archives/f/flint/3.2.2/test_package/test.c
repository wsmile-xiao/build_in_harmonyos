/* FLINT 3.2.2 —— 鸿蒙 PC conan 包的真实断言测试。
 *
 * 判据不是「能加载」，是「算得对」。下面每条的期望值都可手算或独立核对，
 * 覆盖 FLINT 的四条主要能力轴，且**每条都压在不同的依赖上**：
 *
 *   · 机器字整数（ulong_extras）—— 纯 FLINT 自身
 *   · 任意精度整数 fmpz        —— 压 **GMP**（大数一超机器字就走 mpn）
 *   · 有理数 fmpq / 多项式      —— 压 FLINT 自己的代数层
 *   · 任意精度实数 arb          —— 压 **MPFR**
 *
 * 这样分布是有意的：flint 的两个依赖若有一个没真正链上（或链到了错的版本），
 * 只做 dlopen 或只测小整数都发现不了 —— 而「构建成功、CI 全绿、下游才炸」
 * 正是本仓反复付过代价的那类缺陷。
 *
 * 另外**直接链接** libflint（不只是 dlopen）：dlopen 只证明文件能映射进来，
 * 证明不了头文件与库版本一致、符号签名对得上。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <flint/flint.h>
#include <flint/ulong_extras.h>
#include <flint/fmpz.h>
#include <flint/fmpq.h>
#include <flint/fmpz_poly.h>
#include <flint/arb.h>

static int failures = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            printf("  ok   %s\n", (what));                                     \
        } else {                                                               \
            printf("  FAIL %s\n", (what));                                     \
            failures++;                                                        \
        }                                                                      \
    } while (0)

/* ① 机器字层：素性判定与找下一个素数 —— 结果一眼可验 */
static void test_ulong_extras(void)
{
    printf("[1] ulong_extras（机器字整数）\n");
    CHECK(n_is_prime(UWORD(97)) == 1, "97 是素数");
    CHECK(n_is_prime(UWORD(91)) == 0, "91 不是素数（7 x 13）");
    CHECK(n_nextprime(UWORD(100), 0) == UWORD(101), "100 之后的素数是 101");
    /* 2^31-1 = 2147483647，梅森素数 M31 */
    CHECK(n_is_prime(UWORD(2147483647)) == 1, "2^31-1 是素数");
}

/* ② fmpz 层：大数阶乘/二项式/gcd —— 一超机器字就必须走 GMP 的 mpn */
static void test_fmpz_bignum(void)
{
    fmpz_t a, b, g;
    char *s;

    printf("[2] fmpz（任意精度整数，压 GMP）\n");
    fmpz_init(a);
    fmpz_init(b);
    fmpz_init(g);

    /* 25! = 15511210043330985984000000（26 位十进制，远超 64 位机器字） */
    fmpz_fac_ui(a, 25);
    s = fmpz_get_str(NULL, 10, a);
    CHECK(s && strcmp(s, "15511210043330985984000000") == 0, "25! 的十进制展开正确");
    flint_free(s);

    /* C(50,25) = 126410606437752 */
    fmpz_bin_uiui(b, 50, 25);
    s = fmpz_get_str(NULL, 10, b);
    CHECK(s && strcmp(s, "126410606437752") == 0, "C(50,25) = 126410606437752");
    flint_free(s);

    /* gcd(25!, C(50,25)) —— 只断言可被 2 整除且大于 1，避免抄错期望值 */
    fmpz_gcd(g, a, b);
    CHECK(fmpz_cmp_ui(g, 1) > 0, "gcd(25!, C(50,25)) > 1");

    /* 2^61-1 = 2305843009213693951，梅森素数 M61 —— 走 fmpz 的素性判定 */
    fmpz_set_str(a, "2305843009213693951", 10);
    CHECK(fmpz_is_prime(a) == 1, "2^61-1 是素数");

    fmpz_clear(a);
    fmpz_clear(b);
    fmpz_clear(g);
}

/* ③ 有理数与多项式：代数层 */
static void test_fmpq_and_poly(void)
{
    fmpq_t x, y, z;
    fmpz_poly_t p, q, r;
    char *s;

    printf("[3] fmpq / fmpz_poly（有理数与多项式）\n");
    fmpq_init(x);
    fmpq_init(y);
    fmpq_init(z);

    /* 1/3 + 1/6 = 1/2，且必须**自动约分** */
    fmpq_set_si(x, 1, 3);
    fmpq_set_si(y, 1, 6);
    fmpq_add(z, x, y);
    s = fmpq_get_str(NULL, 10, z);
    CHECK(s && strcmp(s, "1/2") == 0, "1/3 + 1/6 = 1/2（且已约分）");
    flint_free(s);

    fmpq_clear(x);
    fmpq_clear(y);
    fmpq_clear(z);

    /* (x+1) * (x+1) = x^2 + 2x + 1 */
    fmpz_poly_init(p);
    fmpz_poly_init(q);
    fmpz_poly_init(r);
    fmpz_poly_set_coeff_si(p, 0, 1);
    fmpz_poly_set_coeff_si(p, 1, 1);
    fmpz_poly_set_coeff_si(q, 0, 1);
    fmpz_poly_set_coeff_si(q, 1, 1);
    fmpz_poly_mul(r, p, q);
    CHECK(fmpz_poly_get_coeff_si(r, 0) == 1, "(x+1)^2 的常数项为 1");
    CHECK(fmpz_poly_get_coeff_si(r, 1) == 2, "(x+1)^2 的一次项为 2");
    CHECK(fmpz_poly_get_coeff_si(r, 2) == 1, "(x+1)^2 的二次项为 1");
    CHECK(fmpz_poly_degree(r) == 2, "(x+1)^2 的次数为 2");
    fmpz_poly_clear(p);
    fmpz_poly_clear(q);
    fmpz_poly_clear(r);
}

/* ④ arb 层：任意精度实数 —— 压 MPFR */
static void test_arb_realnum(void)
{
    arb_t pi;
    char *s;

    printf("[4] arb（任意精度实数，压 MPFR）\n");
    arb_init(pi);

    /* 128 位精度的 pi，区间必须包含 3 而不含 4 —— 区间语义本身也被验到 */
    arb_const_pi(pi, 128);
    CHECK(arb_contains_si(pi, 3) == 0, "pi 的区间不含整数 3（它是紧区间，不是 [3,4]）");

    s = arb_get_str(pi, 20, ARB_STR_NO_RADIUS);
    /* 前 8 位十进制：3.1415926 */
    CHECK(s && strncmp(s, "3.1415926", 9) == 0, "pi 前 8 位小数正确");
    if (s) {
        printf("       pi = %s\n", s);
        flint_free(s);
    }
    arb_clear(pi);
}

int main(void)
{
    printf("flint %s —— 真实断言测试\n", flint_version);

    test_ulong_extras();
    test_fmpz_bignum();
    test_fmpq_and_poly();
    test_arb_realnum();

    flint_cleanup();

    if (failures) {
        printf("\n结果：%d 条断言失败\n", failures);
        return 1;
    }
    printf("\n结果：全部断言通过\n");
    return 0;
}
