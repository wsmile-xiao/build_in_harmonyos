#include <stdio.h>
#include <stdlib.h>
#include "arb.h"

/*
 * test_package: 真实调用 arb 公共 API 的 L1 冒烟测试。
 * 通过区间算术验证 sin(pi/6) 包含 1/2 与 (sqrt(2))^2 包含 2,
 * 证明库可编译、链接并正常运行（非空壳）。
 */
int main(void)
{
    arb_t x, y, z, half;
    slong prec = 128;
    int ok = 1;

    arb_init(x);
    arb_init(y);
    arb_init(z);
    arb_init(half);

    /* y = sin(pi/6), 期望包含 1/2 */
    arb_const_pi(x, prec);         /* x = pi */
    arb_div_ui(x, x, 6, prec);     /* x = pi/6 */
    arb_sin(y, x, prec);
    arb_set_ui(half, 1);
    arb_mul_2exp_si(half, half, -1); /* half = 1/2 (精确区间) */
    if (!arb_contains(y, half))
    {
        printf("FAIL: sin(pi/6) does not contain 1/2\n");
        ok = 0;
    }

    /* z = (sqrt(2))^2, 期望包含 2 */
    arb_set_ui(x, 2);
    arb_sqrt(y, x, prec);
    arb_mul(z, y, y, prec);
    if (!arb_contains_si(z, 2))
    {
        printf("FAIL: sqrt(2)^2 does not contain 2\n");
        ok = 0;
    }

    arb_clear(x);
    arb_clear(y);
    arb_clear(z);
    arb_clear(half);

    if (ok)
    {
        printf("test arb 2.9.0: OK (sin(pi/6)=1/2, sqrt(2)^2=2)\n");
        return 0;
    }
    return 1;
}
