/* FFTW 3.3.10 鸿蒙 PC 适配验证。
 * R34：直接 #include <fftw3.h> 并链接 libfftw3，做**真实变换并校验数值**。 */
#include <fftw3.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

#define N 8
int main(void) {
    char buf[192];
    printf("FFTW %s\n\n", fftw_version);

    /* ① 单频正弦的 DFT：应只在 k=1 与 k=N-1 有非零幅值 */
    {
        fftw_complex *in  = fftw_malloc(sizeof(fftw_complex) * N);
        fftw_complex *out = fftw_malloc(sizeof(fftw_complex) * N);
        for (int i = 0; i < N; i++) {
            in[i][0] = cos(2.0 * M_PI * i / N);   /* 实部：cos(2πi/N) */
            in[i][1] = 0.0;
        }
        fftw_plan p = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);
        check(p != NULL, "fftw_plan_dft_1d 建计划", NULL);
        fftw_execute(p);
        /* cos 的 DFT：X[1] = X[N-1] = N/2，其余 ~0 */
        double m1 = hypot(out[1][0], out[1][1]);
        double m7 = hypot(out[N-1][0], out[N-1][1]);
        double m3 = hypot(out[3][0], out[3][1]);
        snprintf(buf, sizeof(buf), "|X[1]|=%.4f |X[7]|=%.4f 期望 4.0；|X[3]|=%.2e 期望 ~0",
                 m1, m7, m3);
        check(fabs(m1 - N/2.0) < 1e-9 && fabs(m7 - N/2.0) < 1e-9 && m3 < 1e-9,
              "正变换：cos 的频谱只在 k=1,N-1 有峰", buf);
        fftw_destroy_plan(p);
        fftw_free(in); fftw_free(out);
    }

    /* ② 正变换→逆变换往返，应还原原始信号（FFTW 逆变换不归一化，需除以 N） */
    {
        double orig[N];
        fftw_complex *a = fftw_malloc(sizeof(fftw_complex) * N);
        fftw_complex *b = fftw_malloc(sizeof(fftw_complex) * N);
        for (int i = 0; i < N; i++) { orig[i] = i * 1.5 - 3.0; a[i][0] = orig[i]; a[i][1] = 0; }
        fftw_plan f = fftw_plan_dft_1d(N, a, b, FFTW_FORWARD,  FFTW_ESTIMATE);
        fftw_plan r = fftw_plan_dft_1d(N, b, a, FFTW_BACKWARD, FFTW_ESTIMATE);
        fftw_execute(f); fftw_execute(r);
        double maxerr = 0;
        for (int i = 0; i < N; i++) {
            double v = a[i][0] / N;
            double e = fabs(v - orig[i]);
            if (e > maxerr) maxerr = e;
        }
        snprintf(buf, sizeof(buf), "最大误差 %.2e", maxerr);
        check(maxerr < 1e-12, "正逆变换往返还原原始信号", buf);
        fftw_destroy_plan(f); fftw_destroy_plan(r);
        fftw_free(a); fftw_free(b);
    }

    /* ③ 实数到复数变换（r2c），cvxopt 的 fftw 模块会用到 */
    {
        double *in = fftw_malloc(sizeof(double) * N);
        fftw_complex *out = fftw_malloc(sizeof(fftw_complex) * (N/2 + 1));
        for (int i = 0; i < N; i++) in[i] = 1.0;          /* 常量信号 */
        fftw_plan p = fftw_plan_dft_r2c_1d(N, in, out, FFTW_ESTIMATE);
        fftw_execute(p);
        /* 常量信号：仅直流分量 X[0] = N，其余为 0 */
        snprintf(buf, sizeof(buf), "X[0]=%.4f 期望 %d；|X[1]|=%.2e 期望 ~0",
                 out[0][0], N, hypot(out[1][0], out[1][1]));
        check(fabs(out[0][0] - N) < 1e-12 && hypot(out[1][0], out[1][1]) < 1e-12,
              "r2c 变换：常量信号只有直流分量", buf);
        fftw_destroy_plan(p);
        fftw_free(in); fftw_free(out);
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}
