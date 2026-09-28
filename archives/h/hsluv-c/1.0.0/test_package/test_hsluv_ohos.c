#include <stdio.h>
#include <math.h>
#include "hsluv.h"

/* 鸿蒙专项测试：在 OHOS(aarch64) 工具链下验证库的数值性质，
 * 与上游快照对照测试互补——本测试不做任何快照，
 * 而是断言变换的不变量与边界行为（灰度轴、色相环绕、往返闭包）。 */

#define EPS 1e-9

static int close_enough(double a, double b)
{
    return fabs(a - b) < EPS;
}

int main(void)
{
    double r, g, b, h, s, l, r2, g2, b2;
    int i, ok = 1;

    /* 1) 灰度轴：s=0 时 hue 无定义应落 0，rgb 三通道相等 */
    hsluv2rgb(0.0, 0.0, 50.0, &r, &g, &b);
    printf("hsluv2rgb(0,0,50) -> r=%f g=%f b=%f\n", r, g, b);
    if (!close_enough(r, g) || !close_enough(g, b)) {
        fprintf(stderr, "FAIL: achromatic axis not neutral\n");
        ok = 0;
    }
    rgb2hsluv(0.5, 0.5, 0.5, &h, &s, &l);
    printf("rgb2hsluv(.5,.5,.5) -> h=%f s=%f l=%f\n", h, s, l);
    if (s > EPS) {
        fprintf(stderr, "FAIL: gray maps to nonzero saturation\n");
        ok = 0;
    }

    /* 2) 往返闭包：网格上 hsluv->rgb->hsluv 应还原原值（hue 允许 360 环绕） */
    for (i = 0; i <= 20; i++) {
        double hh = (i * 18.0) + 0.5;      /* 0.5 .. 360.5 覆盖环绕 */
        double ss = ((i % 5) * 25.0) + 0.1;
        double ll = 30.0 + (i % 7) * 10.0;
        hsluv2rgb(hh, ss, ll, &r, &g, &b);
        rgb2hsluv(r, g, b, &h, &s, &l);
        {
            double hd = fabs(h - hh);
            if (hd > 180.0)
                hd = 360.0 - hd;
            if (hd > 1e-6 || !close_enough(s, ss) || !close_enough(l, ll)) {
                fprintf(stderr, "FAIL: round-trip at i=%d\n", i);
                ok = 0;
            }
        }
    }
    printf("round-trip grid: 21 points ok\n");

    /* 3) 端点：黑/白 */
    hsluv2rgb(0.0, 0.0, 0.0, &r, &g, &b);
    if (!close_enough(r, 0.0) || !close_enough(g, 0.0) || !close_enough(b, 0.0)) {
        fprintf(stderr, "FAIL: black endpoint\n");
        ok = 0;
    }
    hsluv2rgb(0.0, 0.0, 100.0, &r, &g, &b);
    if (!close_enough(r, 1.0) || !close_enough(g, 1.0) || !close_enough(b, 1.0)) {
        fprintf(stderr, "FAIL: white endpoint\n");
        ok = 0;
    }

    /* 4) HPLuv 往返闭包（与 hsluv 同网格） */
    for (i = 0; i <= 10; i++) {
        double hh = i * 36.0 + 1.0, ss = 50.0 + (i % 3) * 20.0, ll = 40.0 + i * 2.0;
        hpluv2rgb(hh, ss, ll, &r, &g, &b);
        rgb2hpluv(r, g, b, &h, &s, &l);
        {
            double hd = fabs(h - hh);
            if (hd > 180.0)
                hd = 360.0 - hd;
            if (hd > 1e-6 || !close_enough(s, ss) || !close_enough(l, ll)) {
                fprintf(stderr, "FAIL: hpluv round-trip at i=%d\n", i);
                ok = 0;
            }
        }
    }
    printf("hpluv round-trip grid: 11 points ok\n");

    /* 5) rgb2hsluv->hsluv2rgb 一次完整往返还原 rgb（除去色域外黑点） */
    for (i = 0; i < 100; i++) {
        r = (i % 10) / 9.0;
        g = ((i / 10) % 10) / 9.0;
        b = (i / 100) / 1.0;
        rgb2hsluv(r, g, b, &h, &s, &l);
        hsluv2rgb(h, s, l, &r2, &g2, &b2);
        if (!close_enough(r, r2) || !close_enough(g, g2) || !close_enough(b, b2)) {
            fprintf(stderr, "FAIL: rgb restore at i=%d (r=%f vs r2=%f)\n", i, r, r2);
            ok = 0;
        }
    }
    printf("rgb restore grid: 100 points ok\n");

    printf(ok ? "OHOS_TEST_PASS\n" : "OHOS_TEST_FAIL\n");
    return ok ? 0 : 1;
}