/*
 * arb 2.9.0 消费者用例 — 模拟业务上层组件
 *
 * 仅通过库已安装/导出的公共头文件 arb.h 与公开 API 使用 arb:
 *   arb_init / arb_const_pi / arb_div_ui / arb_sin / arb_get_d /
 *   arb_contains_si / arb_clear
 * 验证第三方使用者能否编译、链接、调用并正常运行,并得到
 * 可观察的业务结果(区间算术求 sin(pi/6) ≈ 0.5)。
 */
#include <stdio.h>
#include <math.h>
#include "arb.h"

int main(void)
{
    arb_t x, y, half, mid;
    slong prec = 128;
    double approx;
    int ok = 1;

    arb_init(x);
    arb_init(y);
    arb_init(half);
    arb_init(mid);

    /* x = pi/6 */
    arb_const_pi(x, prec);
    arb_div_ui(x, x, 6, prec);

    /* y = sin(x), 区间应包含 1/2 */
    arb_sin(y, x, prec);
    arb_set_ui(half, 1);
    arb_mul_2exp_si(half, half, -1);

    if (!arb_contains(y, half))
    {
        printf("consumer FAIL: sin(pi/6) interval does not contain 1/2\n");
        ok = 0;
    }

    /* 可观察结果: 取区间中点的 double 近似并核对误差 */
    arb_get_mid_arb(mid, y);
    approx = arf_get_d(arb_midref(mid), ARF_RND_NEAR);
    if (fabs(approx - 0.5) > 1e-12)
    {
        printf("consumer FAIL: |mid(sin(pi/6)) - 0.5| = %.3e > 1e-12\n",
               fabs(approx - 0.5));
        ok = 0;
    }

    printf("consumer: sin(pi/6) mid ≈ %.17g, interval contains 1/2 -> %s\n",
           approx, ok ? "PASS" : "FAIL");

    arb_clear(x);
    arb_clear(y);
    arb_clear(half);
    arb_clear(mid);
    return ok ? 0 : 1;
}