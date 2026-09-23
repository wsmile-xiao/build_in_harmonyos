/* 消费者测试（从最终 Conan 包编译链接）：
 * 断言区间语义本身——包含性、端点顺序、宽度、精度、边界行为（零/负数/无穷/NaN）。
 * oracle 用"高精度参考值被区间包含"（任务规范：不得用 double 精确相等替代区间正确性）。
 * 只使用从 mpfi.h 1.5.4 全文核实过的 API。
 */
#include <stdio.h>
#include <string.h>
#include <mpfr.h>
#include <mpfi.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
} while (0)

static void test_point_and_plain_interval(void)
{
    mpfi_t pt, iv;
    mpfr_t l, r;
    mpfi_init2(pt, 53);
    mpfi_init2(iv, 53);
    mpfr_init2(l, 53); mpfr_init2(r, 53);

    /* 点区间：set_si(2) → [2,2] */
    mpfi_set_si(pt, 2);
    mpfi_get_left(l, pt);
    mpfi_get_right(r, pt);
    CHECK(mpfr_cmp_si(l, 2) == 0 && mpfr_cmp_si(r, 2) == 0,
          "点区间 set_si(2) 应为 [2,2]");
    CHECK(mpfr_cmp(l, r) <= 0, "点区间左端 <= 右端");

    /* 普通区间：interv_si(1,2) → [1,2] */
    mpfi_interv_si(iv, 1, 2);
    mpfi_get_left(l, iv);
    mpfi_get_right(r, iv);
    CHECK(mpfr_cmp_si(l, 1) == 0 && mpfr_cmp_si(r, 2) == 0,
          "interv_si(1,2) 应为 [1,2]");
    CHECK(mpfi_is_inside_si(1, iv) && mpfi_is_inside_si(2, iv),
          "端点 1、2 应在 [1,2] 内");
    CHECK(mpfi_is_inside_si(3, iv) == 0, "3 不应在 [1,2] 内");

    /* 点区间作为区间成员：[2,2] ⊂ [1,2] */
    CHECK(mpfi_is_inside(pt, iv), "[2,2] 应含于 [1,2]");

    mpfi_clear(pt); mpfi_clear(iv);
    mpfr_clear(l); mpfr_clear(r);
}

static void test_arithmetic_includes_truth(void)
{
    /* 运算区间 53 位、oracle 用 300 位独立计算，
     * 断言真值被结果区间包含（对外舍入正确性的直接验证），
     * 而不是拿单一 double 比相等。 */
    mpfi_t a, b, res;
    mpfr_t oracle, lo, hi;
    mpfi_init2(a, 53); mpfi_init2(b, 53); mpfi_init2(res, 53);
    mpfr_init2(oracle, 300);
    mpfr_init2(lo, 53); mpfr_init2(hi, 53);

    /* 加：[0.1,0.2] + [0.3,0.4] → [0.4,0.6]（数学真值）。
     * 0.1/0.2/0.3/0.4 均无法用二进制 53 位精确表示 → 必须向外舍入，
     * 断言 300 位 oracle 端点 0.4 与 0.6 都落在结果区间内。 */
    mpfi_interv_d(a, 0.1, 0.2);
    mpfi_interv_d(b, 0.3, 0.4);
    mpfi_add(res, a, b);
    mpfr_set_d(oracle, 0.4, MPFR_RNDN);
    CHECK(mpfi_is_inside_fr(oracle, res), "真值 0.4 应含于 [0.1,0.2]+[0.3,0.4]");
    mpfr_set_d(oracle, 0.6, MPFR_RNDN);
    CHECK(mpfi_is_inside_fr(oracle, res), "真值 0.6 应含于 [0.1,0.2]+[0.3,0.4]");

    /* 减：[3,7]-[1,2] → [1,6]（全精确） */
    mpfi_interv_si(a, 3, 7); mpfi_interv_si(b, 1, 2);
    mpfi_sub(res, a, b);
    mpfi_get_left(lo, res); mpfi_get_right(hi, res);
    CHECK(mpfr_cmp_si(lo, 1) == 0 && mpfr_cmp_si(hi, 6) == 0,
          "[3,7]-[1,2] 应为 [1,6]");

    /* 乘：[1,2]×[1,2] → [1,4]（精确） */
    mpfi_interv_si(a, 1, 2); mpfi_interv_si(b, 1, 2);
    mpfi_mul(res, a, b);
    mpfi_get_left(lo, res); mpfi_get_right(hi, res);
    CHECK(mpfr_cmp_si(lo, 1) == 0 && mpfr_cmp_si(hi, 4) == 0,
          "[1,2]*[1,2] 应为 [1,4]");

    /* 乘的包含性（非精确情形）：[0.1,0.2]×[0.1,0.2]，
     * 真值端点 0.01 与 0.04 都须被 53 位区间包含 */
    mpfi_interv_d(a, 0.1, 0.2);
    mpfi_mul(res, a, a);
    mpfr_set_d(oracle, 0.01, MPFR_RNDN);
    CHECK(mpfi_is_inside_fr(oracle, res), "真值 0.01 应含于 [0.1,0.2]^2");
    mpfr_set_d(oracle, 0.04, MPFR_RNDN);
    CHECK(mpfi_is_inside_fr(oracle, res), "真值 0.04 应含于 [0.1,0.2]^2");

    /* 除：[3,7]/[2,3] → [1, 3.5]，端点精确 */
    mpfi_interv_si(a, 3, 7); mpfi_interv_si(b, 2, 3);
    mpfi_div(res, a, b);
    mpfi_get_left(lo, res); mpfi_get_right(hi, res);
    CHECK(mpfr_cmp_si(lo, 1) == 0, "[3,7]/[2,3] 左端 = 1");
    {
        mpfr_t x2;
        mpfr_init2(x2, 53);
        mpfr_mul_ui(x2, hi, 2, MPFR_RNDN);
        CHECK(mpfr_cmp_ui(x2, 7) == 0, "[3,7]/[2,3] 右端 = 3.5（×2=7）");
        mpfr_clear(x2);
    }

    /* 开方：[2,4] 开方 → [sqrt(2), 2]。
     * sqrt(2) 不可精确表示 → 300 位 oracle 必须落在区间内，
     * 且左端 <= 真值（向下舍入）、右端 = 2（精确）。 */
    mpfi_interv_si(a, 2, 4);
    mpfi_sqrt(res, a);
    mpfr_set_ui(oracle, 2, MPFR_RNDN);
    mpfr_sqrt(oracle, oracle, MPFR_RNDN); /* 300 位 sqrt(2) */
    CHECK(mpfi_is_inside_fr(oracle, res), "sqrt(2) 300位真值应含于 sqrt([2,4])");
    mpfi_get_left(lo, res); mpfi_get_right(hi, res);
    CHECK(mpfr_cmp_si(hi, 2) == 0, "sqrt([2,4]) 右端 = 2");
    CHECK(mpfr_cmp(lo, oracle) <= 0, "sqrt([2,4]) 左端 <= 真值 sqrt(2)");

    /* 圆周率常量：mpfi_const_pi 在 53 位下必须包含 300 位 π 真值 */
    mpfi_const_pi(res);
    mpfr_const_pi(oracle, MPFR_RNDN);
    CHECK(mpfi_is_inside_fr(oracle, res), "300位 π 真值应含于 53位 mpfi_const_pi");

    mpfi_clear(a); mpfi_clear(b); mpfi_clear(res);
    mpfr_clear(oracle); mpfr_clear(lo); mpfr_clear(hi);
}

static void test_order_and_width(void)
{
    mpfi_t iv;
    mpfr_t l, r, d;
    mpfi_init2(iv, 53);
    mpfr_init2(l, 53); mpfr_init2(r, 53); mpfr_init2(d, 53);

    mpfi_interv_si(iv, 1, 2);
    mpfi_get_left(l, iv); mpfi_get_right(r, iv);
    CHECK(mpfr_cmp(l, r) < 0, "[1,2] 左端 < 右端");

    /* 绝对宽度：diam_abs([1,2]) = 1（diam 是相对直径 (r-l)/|m|，
     * 绝对宽度须用 diam_abs —— mpfi 1.5.4 API 实测语义） */
    mpfi_diam_abs(d, iv);
    CHECK(mpfr_cmp_si(d, 1) == 0, "[1,2] 绝对宽度 = 1");

    /* 逆序端点：interv_si(2,1) 端点被自动整理为 [1,2]。
     * 依据（三重核实，2026-09-10）：
     * - 文档：doc/mpfi.texi L1605-1608 "The values of op1 and op2 are given
     *   in any order, the left endpoint of rop is always the minimum"；
     * - 源码：src/interv_si.c 显式 if (b <= c) 分支，else 支路交换 b/c
     *   （mpfr_set_si 不产生 NaN，不可能构造空区间）；
     * - 实测：探针 interv_si(2,1)→[1,2]、interv_si(5,1)→[1,5]、
     *   interv_si(-1,-5)→[-5,-1]，全部 is_empty=0。 */
    mpfi_interv_si(iv, 2, 1);
    mpfi_get_left(l, iv); mpfi_get_right(r, iv);
    CHECK(mpfr_cmp_si(l, 1) == 0 && mpfr_cmp_si(r, 2) == 0,
          "interv_si(2,1) 端点应被整理为 [1,2]");

    mpfi_clear(iv); mpfr_clear(l); mpfr_clear(r); mpfr_clear(d);
}

static void test_precision(void)
{
    mpfi_t iv;
    mpfi_init2(iv, 100);
    CHECK(mpfi_get_prec(iv) == 100, "init2(100) 后 get_prec = 100");

    mpfi_set_prec(iv, 200);
    CHECK(mpfi_get_prec(iv) == 200, "set_prec(200) 后 get_prec = 200");

    /* round_prec 收窄后真值区间仍须被包含（向外交） */
    mpfi_interv_si(iv, 1, 2);
    mpfi_round_prec(iv, 10);
    CHECK(mpfi_get_prec(iv) == 10, "round_prec(10) 后精度 = 10");
    CHECK(mpfi_is_inside_si(1, iv) && mpfi_is_inside_si(2, iv),
          "round_prec 后 [1,2] 端点真值仍被包含");

    mpfi_clear(iv);
}

static void test_edge_behavior(void)
{
    mpfi_t a, b, res;
    mpfr_t l, r;
    mpfi_init2(a, 53); mpfi_init2(b, 53); mpfi_init2(res, 53);
    mpfr_init2(l, 53); mpfr_init2(r, 53);

    /* 零：[0,0] × [1,2] = [0,0]（mul.c 显式短路：0 乘任何区间仍为 0） */
    mpfi_interv_si(a, 0, 0);
    mpfi_interv_si(b, 1, 2);
    mpfi_mul(res, a, b);
    mpfi_get_left(l, res); mpfi_get_right(r, res);
    CHECK(mpfr_zero_p(l) && mpfr_zero_p(r), "[0,0]*[1,2] = [0,0]");

    /* 零除数：[1,2]/[0,0] → 整个区间 ]-inf,+inf[（div.c 显式分支） */
    mpfi_interv_si(a, 1, 2);
    mpfi_interv_si(b, 0, 0);
    mpfi_div(res, a, b);
    mpfi_get_left(l, res); mpfi_get_right(r, res);
    CHECK(mpfr_inf_p(l) && mpfr_sgn(l) < 0 && mpfr_inf_p(r) && mpfr_sgn(r) > 0,
          "[1,2]/[0,0] = ]-inf,+inf[");

    /* 负数开方：sqrt([-1,4]) 部分负 → NaN（sqrt.c：负左端由 MPFR 产生 NaN） */
    mpfi_interv_si(a, -1, 4);
    mpfi_sqrt(res, a);
    CHECK(mpfi_nan_p(res), "sqrt([-1,4]) 部分负 → NaN");

    /* 负区间乘法：[1,2]*[-3,-1] = [-6,-1] */
    mpfi_interv_si(a, 1, 2);
    mpfi_interv_si(b, -3, -1);
    mpfi_mul(res, a, b);
    mpfi_get_left(l, res); mpfi_get_right(r, res);
    CHECK(mpfr_cmp_si(l, -6) == 0 && mpfr_cmp_si(r, -1) == 0,
          "[1,2]*[-3,-1] = [-6,-1]");

    /* 无穷：右端 +inf 的区间 —— inf_p=1、无界、大数仍含于内 */
    mpfi_interv_si(a, 1, 2);
    mpfr_set_inf(&(a->right), 1); /* 区间内部即两个 mpfr，直接设右端点 */
    CHECK(mpfi_inf_p(a), "右端 +inf 的区间 inf_p = 1");
    CHECK(!mpfi_bounded_p(a), "右端 +inf 的区间无界");
    CHECK(mpfi_is_inside_d(1e300, a), "1e300 应含于 [1,+inf)");

    /* has_zero */
    mpfi_interv_si(a, -1, 1);
    CHECK(mpfi_has_zero(a), "[-1,1] 含零");
    mpfi_interv_si(a, 2, 3);
    CHECK(!mpfi_has_zero(a), "[2,3] 不含零");

    /* 非法区间：interv_si(5,1) 端点整理后为合法区间、非 empty */
    mpfi_interv_si(a, 5, 1);
    CHECK(!mpfi_is_empty(a), "interv_si(5,1) 整理后为合法区间非 empty");

    mpfi_clear(a); mpfi_clear(b); mpfi_clear(res);
    mpfr_clear(l); mpfr_clear(r);
}

int main(void)
{
    printf("mpfi %s consumer test start\n", mpfi_get_version());
    CHECK(strcmp(mpfi_get_version(), "1.5.4") == 0, "版本应为 1.5.4");

    test_point_and_plain_interval();
    test_arithmetic_includes_truth();
    test_order_and_width();
    test_precision();
    test_edge_behavior();

    if (failures) {
        fprintf(stderr, "%d FAILURES\n", failures);
        return 1;
    }
    printf("mpfi consumer tests: ALL PASS\n");
    return 0;
}
