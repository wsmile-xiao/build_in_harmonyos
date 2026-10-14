/* test_dsp.c — libosmo-dsp/0.5.0 消费者探针（复数向量核心 API）
 *
 * 调用上游公开 API（include/osmocom/dsp/cxvec.h、cxvec_math.h）：
 *   osmo_cxvec_alloc / osmo_cxvec_free            （库，cxvec.c）
 *   osmo_cxvec_scale                               （库，cxvec_math.c）
 *   osmo_normsqf / M_PIf                           （头文件内联，cxvec_math.h）
 * 断言：8 点单位幅值复向量经 scale(2+0i) 后总能量 = 4 * N（float 容差）。
 */
#include <osmocom/dsp/cxvec.h>
#include <osmocom/dsp/cxvec_math.h>
#include <complex.h>
#include <math.h>
#include <stdio.h>

static float total_energy(const struct osmo_cxvec *cv)
{
    float e = 0.0f;
    int i;
    for (i = 0; i < cv->len; i++)
        e += osmo_normsqf(cv->data[i]);   /* 头文件内联 |c|^2 */
    return e;
}

int main(void)
{
    const int N = 8;
    struct osmo_cxvec *cv = osmo_cxvec_alloc(N);
    struct osmo_cxvec *out = osmo_cxvec_alloc(N);
    float e_before, e_after;
    int i;

    if (!cv || !out) {
        fprintf(stderr, "FAIL: osmo_cxvec_alloc returned NULL\n");
        return 1;
    }
    for (i = 0; i < N; i++) {
        float ph = 2.0f * M_PIf * (float)i / (float)N;
        cv->data[i] = cosf(ph) + sinf(ph) * I;   /* 单位幅值 */
    }
    cv->len = N;

    e_before = total_energy(cv);
    osmo_cxvec_scale(cv, 2.0f + 0.0f * I, out);  /* 幅值 x2 → 能量 x4 */
    e_after = total_energy(out);

    osmo_cxvec_free(cv);
    osmo_cxvec_free(out);

    if (fabsf(e_before - (float)N) > 1e-3f) {
        fprintf(stderr, "FAIL: energy before=%f expected %d\n", e_before, N);
        return 1;
    }
    if (fabsf(e_after - 4.0f * (float)N) > 1e-2f) {
        fprintf(stderr, "FAIL: energy after=%f expected %f\n", e_after, 4.0f * (float)N);
        return 1;
    }
    printf("PASS: cxvec scale/energy N=8 e=%g -> %g (x4)\n", e_before, e_after);
    return 0;
}
