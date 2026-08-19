/* GMP-ECM 真实断言：用椭圆曲线法把一个手算得出的合数分解开。
 *
 * n = 1000003 × (2^61 - 1)，两个都是素数，大小悬殊：
 * B1=50000 足够找出小的那个，找不出 2^61-1（它减一含大素因子）。
 * 断言拿到的因子严格介于 1 和 n 之间、且整除 n。
 *
 * ECM 是概率算法，两种非结论都按「换条曲线再来」处理，不当失败：
 *   · rc <= 0        —— 这条曲线什么都没找到；
 *   · f == n         —— 一条曲线同时命中全部因子，没把 n 劈开（合法结果，不是错）。
 * 全部曲线跑完仍无所获才判失败。
 */
#include <stdio.h>
#include <stdlib.h>
#include <gmp.h>
#include <ecm.h>

#define SMALL_P 1000003UL
#define BIG_P   "2305843009213693951"   /* 2^61 - 1，梅森素数 */
#define TRIES   30

int main(void) {
    mpz_t n, f, q, r, small;
    mpz_inits(n, f, q, r, small, NULL);
    mpz_set_str(n, BIG_P, 10);
    mpz_mul_ui(n, n, SMALL_P);
    mpz_set_ui(small, SMALL_P);
    gmp_printf("ecm: n = %Zd\n", n);

    int found = 0;
    for (int i = 1; i <= TRIES && !found; ++i) {
        ecm_params p;
        ecm_init(p);
        mpz_set_ui(p->sigma, (unsigned long)(i * 7919));   /* 每轮换一条曲线 */
        mpz_set_ui(f, 0);
        int rc = ecm_factor(f, n, 50000.0, p);
        ecm_clear(p);

        if (rc <= 0) continue;                             /* 这条曲线没找到 */
        if (mpz_cmp(f, n) == 0) continue;                  /* 一次命中全部因子，没劈开 */
        if (mpz_cmp_ui(f, 1) <= 0) {
            gmp_fprintf(stderr, "ecm: 返回的因子 <= 1: %Zd\n", f);
            mpz_clears(n, f, q, r, small, NULL);
            return 1;
        }
        mpz_tdiv_qr(q, r, n, f);
        if (mpz_sgn(r) != 0) {
            gmp_fprintf(stderr, "ecm: %Zd 不整除 n，余 %Zd\n", f, r);
            mpz_clears(n, f, q, r, small, NULL);
            return 1;
        }
        gmp_printf("ecm: 第 %d 条曲线找到因子 %Zd，余因子 %Zd\n", i, f, q);
        /* 这个规模下 B1=50000 只可能找出小的那个素因子 —— 顺带把它钉死 */
        if (mpz_cmp(f, small) != 0 && mpz_cmp(q, small) != 0) {
            gmp_fprintf(stderr, "ecm: 因子既不是 %Zd 也不是它的余因子，结果可疑\n", small);
            mpz_clears(n, f, q, r, small, NULL);
            return 1;
        }
        found = 1;
    }

    if (!found) {
        fprintf(stderr, "ecm: %d 条曲线都没把 n 劈开 —— 库能加载但算不出来\n", TRIES);
        mpz_clears(n, f, q, r, small, NULL);
        return 1;
    }

    printf("ecm: version = %s\n", ecm_version());
    mpz_clears(n, f, q, r, small, NULL);
    printf("ecm: 全部断言通过\n");
    return 0;
}
