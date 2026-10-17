/*
 * test.c — fft-c 3356ecd87d test_package 消费者数值验证
 *
 * 仅使用本包已安装/导出的公开头（<fft.h>）与公开 API：
 *   create_fft_transformer / fft_forward / fft_backward / windowing / cosq
 * 对已知双频信号做真实变换并逐项数值断言（非空壳、非只打印）：
 *   1) 2Hz 正弦（幅值10）在 bin2 谱峰幅值 5.0（FFT_SCALED_OUTPUT）
 *   2) 15Hz 余弦（幅值5）在 bin15 谱峰幅值 2.5
 *   3) 往返：forward(scaled)+backward(scaled) 还原信号（依赖配方携带的上游 bug 补丁）
 *   4) HANNING 窗端点≈0、中点≈1.0
 *   5) cosq transformer 可创建/释放
 * exit 0 = 全部断言通过。
 *
 * 上游 rfftf 输出排布（实测）：out[0]=R0(DC)，out[N-1]=R_{N/2}(Nyquist)，
 * 对 1<=k<=N/2-1：out[2k-1]=R_k，out[2k]=I_k。
 */
#include <fft.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 1024
#define TOL 0.05
#define RT_TOL 1e-8

static int failures = 0;

static void check(const char *label, double got, double expected, double tol)
{
    if (fabs(got - expected) <= tol) {
        printf("[PASS] %s: got=%.6f expected=%.6f\n", label, got, expected);
    } else {
        printf("[FAIL] %s: got=%.6f expected=%.6f (tol=%.6f)\n", label, got, expected, tol);
        failures++;
    }
}

static double mag_at(const FFT_PRECISION *out, int bin)
{
    if (bin == 0) {
        return fabs((double)out[0]);
    }
    double re = out[2 * bin - 1];
    double im = out[2 * bin];
    return sqrt(re * re + im * im);
}

int main(void)
{
    const double PI = 3.14159265358979323846;
    FFT_PRECISION *sig = (FFT_PRECISION *)malloc(N * sizeof(FFT_PRECISION));
    FFT_PRECISION *work = (FFT_PRECISION *)malloc(N * sizeof(FFT_PRECISION));
    if (!sig || !work) { printf("[FATAL] malloc failed\n"); return 2; }

    for (int i = 0; i < N; i++) {
        double v = 10.0 * sin(2 * PI * 2 * i / N) + 5.0 * cos(2 * PI * 15 * i / N);
        sig[i] = (FFT_PRECISION)v;
        work[i] = sig[i];
    }

    FFTTransformer *tr = create_fft_transformer(N, FFT_SCALED_OUTPUT);
    if (!tr) { printf("[FATAL] create_fft_transformer failed\n"); return 2; }
    fft_forward(tr, work);

    check("MAG(bin 2Hz)", mag_at(work, 2), 5.0, TOL);
    check("MAG(bin 15Hz)", mag_at(work, 15), 2.5, TOL);
    check("MAG(DC bin0)", mag_at(work, 0), 0.0, TOL);
    check("MAG(bin1 leakage)", mag_at(work, 1), 0.0, TOL);
    check("MAG(bin3 leakage)", mag_at(work, 3), 0.0, TOL);

    /* 往返一致性（依赖补丁；上游原始代码返回 n*x） */
    fft_backward(tr, work);
    double maxerr = 0.0;
    for (int i = 0; i < N; i++) {
        double e = fabs((double)work[i] - (double)sig[i]);
        if (e > maxerr) maxerr = e;
    }
    check("roundtrip", maxerr, 0.0, RT_TOL);

    free_fft_transformer(tr);

    /* windowing() */
    FFT_PRECISION *ones = (FFT_PRECISION *)malloc(N * sizeof(FFT_PRECISION));
    for (int i = 0; i < N; i++) ones[i] = 1.0;
    FFT_PRECISION *win = windowing(N, ones, HANNING, 1.0);
    if (!win) { printf("[FAIL] windowing returned NULL for HANNING\n"); failures++; }
    else {
        check("HANNING win[0]", win[0], 0.0, TOL);
        check("HANNING win[N/2]", win[N / 2], 1.0, TOL);
        free(win);
    }
    free(ones);

    /* cosq */
    FFTCosqTransformer *ct = create_fft_cosq_transformer(N, FFT_SCALED_OUTPUT);
    if (ct) { free_cosq_fft_transformer(ct); printf("[PASS] cosq create/free\n"); }
    else { printf("[FAIL] cosq create\n"); failures++; }

    free(sig);
    free(work);

    if (failures == 0) {
        printf("ALL 9 ASSERTION GROUPS PASSED\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}