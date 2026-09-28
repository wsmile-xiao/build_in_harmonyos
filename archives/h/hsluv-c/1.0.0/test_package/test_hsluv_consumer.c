#include <stdio.h>
#include <math.h>
#include "hsluv.h"

/* 参考值取自官方 tests/snapshot-rev4.json 中 #ff0000 条目 */
#define REF_H 12.177050630061776
#define REF_S 100.0000000000022
#define REF_L 53.23711559542933
#define REF_HP_S 426.7467891835753   /* hpluv 饱和度（与 hsluv 饱和度不同） */
#define EPS   1e-9

static int close_enough(double a, double b)
{
    return fabs(a - b) < EPS;
}

int main(void)
{
    double h, s, l;
    double r, g, b;
    int ok = 1;

    /* 1) RGB(#ff0000) -> HSLuv，与官方快照对照 */
    rgb2hsluv(1.0, 0.0, 0.0, &h, &s, &l);
    printf("rgb2hsluv(1,0,0) -> h=%f s=%f l=%f\n", h, s, l);
    if (!close_enough(h, REF_H) || !close_enough(s, REF_S) || !close_enough(l, REF_L)) {
        fprintf(stderr, "FAIL: rgb2hsluv mismatch\n");
        ok = 0;
    }

    /* 2) HSLuv -> RGB 往返，还原 #ff0000 */
    hsluv2rgb(REF_H, REF_S, REF_L, &r, &g, &b);
    printf("hsluv2rgb(ref) -> r=%f g=%f b=%f\n", r, g, b);
    if (!close_enough(r, 1.0) || !close_enough(g, 0.0) || !close_enough(b, 0.0)) {
        fprintf(stderr, "FAIL: hsluv2rgb mismatch\n");
        ok = 0;
    }

    /* 3) RGB(#ff0000) -> HPLuv，与官方快照对照；再 HPLuv -> RGB 还原 #ff0000 */
    {
        double h2, s2, l2, r2, g2, b2;
        rgb2hpluv(1.0, 0.0, 0.0, &h2, &s2, &l2);
        printf("rgb2hpluv(1,0,0) -> h=%f s=%f l=%f\n", h2, s2, l2);
        if (!close_enough(h2, REF_H) || !close_enough(s2, REF_HP_S) || !close_enough(l2, REF_L)) {
            fprintf(stderr, "FAIL: rgb2hpluv mismatch\n");
            ok = 0;
        }
        hpluv2rgb(REF_H, REF_HP_S, REF_L, &r2, &g2, &b2);
        printf("hpluv2rgb(ref) -> r=%f g=%f b=%f\n", r2, g2, b2);
        if (!close_enough(r2, 1.0) || !close_enough(g2, 0.0) || !close_enough(b2, 0.0)) {
            fprintf(stderr, "FAIL: hpluv2rgb mismatch\n");
            ok = 0;
        }
    }

    printf(ok ? "CONSUMER_PASS\n" : "CONSUMER_FAIL\n");
    return ok ? 0 : 1;
}
