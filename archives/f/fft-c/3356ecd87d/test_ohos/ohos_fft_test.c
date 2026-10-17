/*
 * ohos_fft_test.c — HarmonyOS PC (aarch64) 专项测试 for fft-c 3356ecd87d
 *
 * 目的：在 HarmonyOS PC (OHOS aarch64) 工具链与运行时上，以数值断言验证
 * fft-c 公开 API 的正确性（非空壳、非复述上游样例）：
 *   1) fft_forward 频谱正确性：已知双频信号（2Hz 正弦 + 15Hz 余弦）在对应
 *      bin 上出现理论幅值（10*sin→5.0，5*cos→2.5，FFT_SCALED_OUTPUT 语义）。
 *   2) 往返一致性：fft_forward(SCALED) + fft_backward(SCALED) 还原原始信号
 *      （依赖 patches/0001-fix-fft-backward-double-scaling.patch 修复上游
 *      fft_backward 的 ×n 双重缩放 bug；未打补丁时往返结果 = n×原信号）。
 *   3) windowing() 窗函数：HANNING 窗在 0 处≈0、中点≈1.0，且返回数组可释放。
 *
 * 上游 __fft_real_forward 的 rfftf 输出排布（实测确认）：
 *   out[0] = R0 (DC)，out[N-1] = R_{N/2} (Nyquist)，
 *   对 1 <= k <= N/2-1：out[2k-1] = R_k，out[2k] = I_k。
 *
 * 编译（OHOS 工具链）：
 *   /data/service/hnp/bin/clang -O2 -Wall -Wextra -o ohos_fft_test \
 *       ohos_fft_test.c fft.c -lm
 * 运行：./ohos_fft_test   （exit 0 = 全部断言通过）
 */
#include "fft.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 1024
#define TOL 0.05
#define ROUNDTRIP_TOL 1e-8

static int failures = 0;

static void check_mag(const char *label, double got, double expected, double tol)
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
    /* 上游 rfftf 排布：out[0]=R0(DC)；1<=bin<=N/2-1 时 R_bin=out[2*bin-1], I_bin=out[2*bin] */
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

    /* 双频信号：10*sin(2Hz) + 5*cos(15Hz)，n=1024 时两频率均为整 bin */
    for (int i = 0; i < N; i++) {
        double v = 10.0 * sin(2 * PI * 2 * i / N) + 5.0 * cos(2 * PI * 15 * i / N);
        sig[i] = (FFT_PRECISION)v;
        work[i] = sig[i];
    }

    /* ---- 1) 频谱正确性 ---- */
    FFTTransformer *tr = create_fft_transformer(N, FFT_SCALED_OUTPUT);
    if (!tr) { printf("[FATAL] create_fft_transformer failed\n"); return 2; }
    fft_forward(tr, work);

    check_mag("MAG(bin 2Hz)", mag_at(work, 2), 5.0, TOL);    /* 10*sin 幅值一半 */
    check_mag("MAG(bin 15Hz)", mag_at(work, 15), 2.5, TOL);  /* 5*cos 幅值一半 */
    check_mag("MAG(DC bin0)", mag_at(work, 0), 0.0, TOL);    /* 零均值信号 */
    check_mag("MAG(bin1 leakage)", mag_at(work, 1), 0.0, TOL);
    check_mag("MAG(bin3 leakage)", mag_at(work, 3), 0.0, TOL);

    /* ---- 2) 往返一致性：forward(scaled)+backward(scaled) 应还原信号 ---- */
    fft_backward(tr, work);
    double maxerr = 0.0;
    for (int i = 0; i < N; i++) {
        double e = fabs((double)work[i] - (double)sig[i]);
        if (e > maxerr) maxerr = e;
    }
    if (maxerr <= ROUNDTRIP_TOL) {
        printf("[PASS] roundtrip: maxerr=%.3e <= %.1e\n", maxerr, ROUNDTRIP_TOL);
    } else {
        printf("[FAIL] roundtrip: maxerr=%.3e > %.1e\n", maxerr, ROUNDTRIP_TOL);
        failures++;
    }
    free_fft_transformer(tr);

    /* ---- 3) windowing(): HANNING 窗端点≈0、中点≈1.0 ---- */
    FFT_PRECISION *ones = (FFT_PRECISION *)malloc(N * sizeof(FFT_PRECISION));
    if (!ones) { printf("[FATAL] malloc failed\n"); return 2; }
    for (int i = 0; i < N; i++) ones[i] = 1.0;
    FFT_PRECISION *win = windowing(N, ones, HANNING, 1.0);
    if (!win) { printf("[FAIL] windowing returned NULL for HANNING\n"); failures++; }
    else {
        check_mag("HANNING win[0]", win[0], 0.0, TOL);
        check_mag("HANNING win[N/2]", win[N / 2], 1.0, TOL);
        free(win);
    }
    free(ones);

    /* ---- 4) cosq 变换 API 可构造/释放（OS 完整性） ---- */
    FFTCosqTransformer *ct = create_fft_cosq_transformer(N, FFT_SCALED_OUTPUT);
    if (ct) { free_cosq_fft_transformer(ct); printf("[PASS] cosq transformer create/free\n"); }
    else { printf("[FAIL] create_fft_cosq_transformer failed\n"); failures++; }

    free(sig);
    free(work);

    if (failures == 0) {
        printf("ALL %d ASSERTION GROUPS PASSED (HarmonyOS aarch64)\n", 9);
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
