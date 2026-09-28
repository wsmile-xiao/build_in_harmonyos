/*
 * consumer_fft_c.c — fft-c 消费者用例（业务场景：主导频率检测）
 *
 * 仅通过本库**已安装/导出**的公开头（<fft.h>）、公开 API 与正常链接目标使用
 * fft-c：构造一个已知频率的离散正弦信号，fft_forward 后按 fft-c 实测的
 * rfftf 输出排布（out[0]=R0(DC), out[N-1]=R_{N/2}, 1<=k<=N/2-1: R_k=out[2k-1],
 * I_k=out[2k]）扫描谱峰，输出检测到的主导频率与幅值，与理论值比对。
 *
 * 不包含库私有头、不调用内部符号、不引用库内部测试构建目录。
 */
#include <fft.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 4096
#define SAMPLE_RATE 4096.0   /* 1Hz 分辨率 */

int main(void)
{
    const double PI = 3.14159265358979323846;
    const double f_target = 17.0; /* 已知主导频率 */
    FFT_PRECISION *x = (FFT_PRECISION *)malloc(N * sizeof(FFT_PRECISION));

    /* 17Hz 正弦 + 少量 3Hz 杂波 + 直流偏置 */
    for (int i = 0; i < N; i++) {
        x[i] = 8.0 * sin(2 * PI * f_target * i / SAMPLE_RATE)
             + 1.5 * sin(2 * PI * 3 * i / SAMPLE_RATE) + 0.2;
    }

    FFTTransformer *tr = create_fft_transformer(N, FFT_SCALED_OUTPUT);
    if (!tr) { fprintf(stderr, "create_fft_transformer failed\n"); return 2; }
    fft_forward(tr, x);

    /* 扫谱峰（实测排布：R_k=out[2k-1], I_k=out[2k]；DC=out[0]） */
    int peak_bin = 0;
    double peak_mag = 0.0;
    for (int k = 1; k < N / 2; k++) {
        double re = x[2 * k - 1];
        double im = x[2 * k];
        double m = sqrt(re * re + im * im);
        if (m > peak_mag) { peak_mag = m; peak_bin = k; }
    }
    double freq = peak_bin * SAMPLE_RATE / N;

    printf("detected dominant frequency: %.2f Hz (bin %d), magnitude %.3f\n",
           freq, peak_bin, peak_mag);
    printf("expected: %.2f Hz, magnitude ~%.3f (8.0*sin/2, scaled)\n",
           f_target, 4.0);

    free_fft_transformer(tr);
    free(x);

    int ok = (fabs(freq - f_target) < 0.5) && (fabs(peak_mag - 4.0) < 0.1);
    if (!ok) {
        fprintf(stderr, "CONSUMER CHECK FAILED\n");
        return 1;
    }
    printf("CONSUMER CHECK PASSED\n");
    return 0;
}