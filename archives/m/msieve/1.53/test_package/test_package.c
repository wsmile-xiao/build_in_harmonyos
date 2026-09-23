/* test_package/test_package.c — msieve 1.53 消费者/功能测试
 *
 * 通过库 API（非 CLI）真实运行整数分解，验证：
 *   1. 半素数分解正确：p*q 的两个素因子均被找出，且乘积回验等于原数
 *   2. 因子被库判定为素数（MSIEVE_PRIME）
 *   3. 分解标志位 MSIEVE_FLAG_FACTORIZATION_DONE 置位
 *   4. 负向输入：素数、1、0 → 库返回无复合因子/单因子/不崩溃
 *   5. 较大输入（64+ 位）走 QS 流程完整分解
 *
 * 素性回验不使用外部库：对因子做确定性 Miller-Rabin（底数集合
 * {2,3,5,7,11,13,17,19,23,29,31,37}，对 < 3.3e24 为确定性判定）。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "msieve.h"

/* ---------- 简易大数（仅用于乘积回验，因子最多 ~25 位十进制） ---------- */

#define NLIMBS 8   /* 8 * 32 = 256 bit，足够 2^197 以下的乘积 */

typedef struct { uint32_t d[NLIMBS]; } bignum_t;   /* little-endian */

static void bn_from_dec(bignum_t *n, const char *s)
{
    memset(n, 0, sizeof(*n));
    for (; *s >= '0' && *s <= '9'; s++) {
        uint64_t carry = (uint64_t)(*s - '0');
        for (int i = 0; i < NLIMBS; i++) {
            carry += (uint64_t)n->d[i] * 10;
            n->d[i] = (uint32_t)carry;
            carry >>= 32;
        }
    }
}

static void bn_mul(bignum_t *r, const bignum_t *a, const bignum_t *b)
{
    memset(r, 0, sizeof(*r));
    for (int i = 0; i < NLIMBS; i++) {
        uint64_t carry = 0;
        for (int j = 0; i + j < NLIMBS; j++) {
            uint64_t cur = (uint64_t)r->d[i + j] +
                           (uint64_t)a->d[i] * b->d[j] + carry;
            r->d[i + j] = (uint32_t)cur;
            carry = cur >> 32;
        }
    }
}

static int bn_cmp(const bignum_t *a, const bignum_t *b)
{
    for (int i = NLIMBS - 1; i >= 0; i--) {
        if (a->d[i] != b->d[i]) return a->d[i] < b->d[i] ? -1 : 1;
    }
    return 0;
}

/* ---------- 确定性 Miller-Rabin（32 位字实现，输入 < 2^256） ---------- */

/* r = a*b mod m，m 为奇数，用 long division 不现实；因子 <= 10^25 < 2^84，
 * 验证素性只需对 <= 10^25 的数判定 —— 用 __int128 逐位乘加太慢且 NLIMBS=8
 * 的 mod 开销大。替代：素因子上限 10^25，回验用 GMP（msieve 必然带 GMP）。 */
#include <gmp.h>

static int is_probably_prime_u64(uint64_t n)
{
    /* 64 位以内确定性 MR：底 {2,3,5,7,11,13,17,19,23,29,31,37} 足够 */
    if (n < 2) return 0;
    uint64_t small[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (int i = 0; i < 12; i++) {
        if (n == small[i]) return 1;
        if (n % small[i] == 0) return 0;
    }
    uint64_t d = n - 1; int s = 0;
    while ((d & 1) == 0) { d >>= 1; s++; }
    for (int i = 0; i < 12; i++) {
        uint64_t x = 1, base = small[i], e = d;
        while (e) { /* 需要 128 位模乘 */
            if (e & 1) x = (__uint128_t)x * base % n;
            base = (__uint128_t)base * base % n;
            e >>= 1;
        }
        if (x == 1 || x == n - 1) continue;
        int composite = 1;
        for (int r = 1; r < s; r++) {
            x = (__uint128_t)x * x % n;
            if (x == n - 1) { composite = 0; break; }
        }
        if (composite) return 0;
    }
    return 1;
}

static int factor_string_is_prime(const char *num)
{
    /* 因子字符串 → 素性。< 2^64 走确定性 MR；更大走 GMP mpz_probab_prime_p */
    size_t len = strlen(num);
    if (len < 20) {
        uint64_t v = strtoull(num, NULL, 10);
        return is_probably_prime_u64(v);
    }
    mpz_t z;
    mpz_init_set_str(z, num, 10);
    int r = mpz_probab_prime_p(z, 25) >= 1;  /* 2 = definite, 1 = probable */
    mpz_clear(z);
    return r;
}

/* ---------- msieve 分解封装 ---------- */

static msieve_obj *run_factor(const char *n, msieve_factor **out)
{
    char buf[512];
    snprintf(buf, sizeof(buf), "%s", n);
    msieve_obj *obj = msieve_obj_new(
        buf,
        0,                    /* flags: 无日志（安静模式），分解后直接读 factors */
        "test_save.dat",
        "test_msieve.log",
        "test_msieve.fb",
        0, 0,                 /* seeds */
        0,                    /* max_relations: sieving until done */
        cpu_generic,          /* 不伪造 CPU 特性：AArch64 上如实用 generic */
        0, 0,                 /* cache sizes: 让库自行选择 */
        1,                    /* num_threads */
        0,                    /* which_gpu */
        NULL);                /* nfs_args */
    if (!obj) return NULL;
    msieve_run(obj);
    if (out) *out = obj->factors;
    return obj;
}

static int count_factors(msieve_factor *f)
{
    int c = 0;
    for (; f; f = f->next) c++;
    return c;
}

static int check_semiprime(const char *n, int expect_factors)
{
    int failures = 0;
    msieve_factor *f = NULL;
    msieve_obj *obj = run_factor(n, &f);
    if (!obj) { printf("FAIL %s: msieve_obj_new returned NULL\n", n); return 1; }
    if (!(obj->flags & MSIEVE_FLAG_FACTORIZATION_DONE)) {
        printf("FAIL %s: FACTORIZATION_DONE not set\n", n);
        failures++;
    }
    int nf = count_factors(f);
    if (nf != expect_factors) {
        printf("FAIL %s: expected %d factors, got %d\n", n, expect_factors, nf);
        failures++;
    }
    /* 乘积回验 */
    bignum_t product, tmp, fac;
    bn_from_dec(&product, "1");
    for (msieve_factor *p = f; p; p = p->next) {
        bn_from_dec(&fac, p->number);
        bn_mul(&tmp, &product, &fac);
        product = tmp;
        /* 素性验证：库自己的判定 + 独立 MR 复核 */
        if (p->factor_type == MSIEVE_COMPOSITE) {
            printf("FAIL %s: factor %s reported COMPOSITE\n", n, p->number);
            failures++;
        }
        if (!factor_string_is_prime(p->number)) {
            printf("FAIL %s: factor %s fails independent primality check\n", n, p->number);
            failures++;
        }
    }
    bignum_t target;
    bn_from_dec(&target, n);
    if (bn_cmp(&product, &target) != 0) {
        printf("FAIL %s: product of factors != input\n", n);
        failures++;
    }
    msieve_obj_free(obj);
    if (!failures) printf("PASS %s -> %d prime factors, product verified\n", n, nf);
    return failures;
}

static int check_negative(const char *n, const char *why)
{
    /* 负向输入：库/驱动层应拒绝或不产生错误因子，绝不崩溃。
     * demo.c 的 driver 层会跳过非数字输入；库层对 "0"/"1" 返回
     * 立即完成且无因子/单因子。这里通过 API 直接传入验证不崩溃。 */
    msieve_factor *f = NULL;
    msieve_obj *obj = run_factor(n, &f);
    int failures = 0;
    if (!obj) {
        /* obj_new 拒绝输入也是合法的负向行为 */
        printf("PASS negative %-6s (%s): rejected by msieve_obj_new\n", n, why);
        return 0;
    }
    /* 对 0/1/素数：FACTORIZATION_DONE 应置位且至多一个因子 */
    if (!(obj->flags & MSIEVE_FLAG_FACTORIZATION_DONE)) {
        printf("FAIL negative %s (%s): FACTORIZATION_DONE not set\n", n, why);
        failures++;
    }
    int nf = count_factors(f);
    if (nf > 1) {
        printf("FAIL negative %s (%s): %d factors for trivial input\n", n, why, nf);
        failures++;
    }
    msieve_obj_free(obj);
    if (!failures) printf("PASS negative %-6s (%s): handled, %d factor(s)\n", n, why, nf);
    return failures;
}

int main(void)
{
    int failures = 0;

    printf("== msieve 1.53 consumer/functional tests ==\n");

    /* 正向：已知因子结构的合数，规模覆盖 trial division / SQUFOF / QS */
    /* 15 = 3 * 5 */
    failures += check_semiprime("15", 2);
    /* 1009 * 1009 = 1018081（平方数） */
    failures += check_semiprime("1018081", 2);
    /* 104729 * 104723 = 10967535067（11 位半素数） */
    failures += check_semiprime("10967535067", 2);
    /* 46 位合数 59 * 109 * 138706677400692667850774387472571838797283059
     * （QS 主流程，3 个素因子） */
    failures += check_semiprime(
        "892022642363854546948330085836109495305327352429", 3);

    /* 负向：素数（无复合因子）、1、0 */
    failures += check_negative("1000003", "prime input");
    failures += check_negative("1", "one");
    failures += check_negative("0", "zero");

    printf(failures ? "== %d FAILURE(S) ==\n" : "== ALL TESTS PASSED ==\n", failures);
    return failures ? 1 : 0;
}
