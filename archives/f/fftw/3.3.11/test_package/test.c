/* FFTW 双精度 double 精度 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 变换算得对。这里真的做一次 DFT，
 * 再跟**解析解**逐点对账 —— 输入取纯余弦，它的离散谱是精确已知的：
 *
 *   x[n] = cos(2π·K·n/N)  的 DFT 只在 k=K 与 k=N-K 处非零，值均为 N/2。
 *
 * 这个判据很紧：任何一处蝶形运算、旋转因子或精度处理出错，
 * 谱线位置或幅值立刻对不上，不会「看起来跑通了」。
 *
 * 另外单独验多线程库（libfftw3_threads）：
 *   · fftw_init_threads() 必须返回非零
 *   · 用 2 线程重算同一变换，结果必须与单线程**逐点一致**
 * 只调用 init_threads 而不比对结果是不够的 —— 线程版算错了它照样返回成功。
 */
#include <fftw3.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 16
#define K 3

typedef double real_t;

/* 各精度的容差不同：float 只有 ~7 位十进制有效数字，
 * 拿 double 的容差去卡它是判据过严，不是库有问题。 */
static const double TOL = 1e-10;

static int check_spectrum(fftw_complex *out, const char *what)
{
    for (int k = 0; k < N; ++k) {
        const double re = (double)out[k][0], im = (double)out[k][1];
        const double want_re = (k == K || k == N - K) ? (double)N / 2.0 : 0.0;
        if (fabs(re - want_re) > TOL || fabs(im) > TOL) {
            printf("FAIL %s: X[%d] = (%.10g, %.10g)，期望 (%.10g, 0)\n",
                   what, k, re, im, want_re);
            return 1;
        }
    }
    return 0;
}

int main(void)
{
    fftw_complex *in  = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex *out = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex *out2 = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * N);
    if (!in || !out || !out2) {
        printf("FAIL fftw_malloc 返回空\n");
        return 1;
    }

    for (int n = 0; n < N; ++n) {
        in[n][0] = (real_t)cos(2.0 * M_PI * (double)K * (double)n / (double)N);
        in[n][1] = (real_t)0.0;
    }

    /* ① 单线程正变换，与解析解对账 */
    {
        fftw_plan p = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);
        if (!p) { printf("FAIL 创建单线程计划失败\n"); return 1; }
        fftw_execute(p);
        fftw_destroy_plan(p);
        if (check_spectrum(out, "单线程正变换")) return 1;
    }

    /* ② 逆变换应还原出 N 倍的原信号（FFTW 的逆变换不做归一化）*/
    {
        fftw_complex *back = (fftw_complex *)fftw_malloc(sizeof(fftw_complex) * N);
        /* 与上面 in/out/out2 一致地检查 —— 漏掉这里的话，FFTW_ESTIMATE 下
         * planner 并不触碰数组，计划照样建得出来，等到 execute 才往 NULL 写，
         * 结果是段错误而不是一条可读的 FAIL。 */
        if (!back) { printf("FAIL fftw_malloc 返回空（逆变换 back 缓冲区）\n"); return 1; }
        fftw_plan p = fftw_plan_dft_1d(N, out, back, FFTW_BACKWARD, FFTW_ESTIMATE);
        if (!p) { printf("FAIL 创建逆变换计划失败\n"); fftw_free(back); return 1; }
        fftw_execute(p);
        fftw_destroy_plan(p);
        for (int n = 0; n < N; ++n) {
            const double want = (double)in[n][0] * (double)N;
            if (fabs((double)back[n][0] - want) > TOL * N ||
                fabs((double)back[n][1]) > TOL * N) {
                printf("FAIL 逆变换 x[%d] = (%.10g, %.10g)，期望 (%.10g, 0)\n",
                       n, (double)back[n][0], (double)back[n][1], want);
                return 1;
            }
        }
        fftw_free(back);
    }

    /* ③ 多线程库：init 必须成功，且**结果与单线程逐点一致**。
     *    这一条验的是 libfftw3_threads 真的被链上且能用 ——
     *    pyfftw 就是按 -lfftw3_threads 探测它的。 */
    {
        if (!fftw_init_threads()) {
            printf("FAIL fftw_init_threads() 返回 0（多线程库不可用）\n");
            return 1;
        }
        fftw_plan_with_nthreads(2);
        fftw_plan p = fftw_plan_dft_1d(N, in, out2, FFTW_FORWARD, FFTW_ESTIMATE);
        if (!p) { printf("FAIL 创建多线程计划失败\n"); return 1; }
        fftw_execute(p);
        fftw_destroy_plan(p);
        if (check_spectrum(out2, "双线程正变换")) return 1;
        for (int k = 0; k < N; ++k) {
            if (fabs((double)out2[k][0] - (double)out[k][0]) > TOL ||
                fabs((double)out2[k][1] - (double)out[k][1]) > TOL) {
                printf("FAIL 双线程与单线程结果不一致于 k=%d\n", k);
                return 1;
            }
        }
        fftw_cleanup_threads();
    }

    fftw_free(in); fftw_free(out); fftw_free(out2);
    printf("fftw3 OK: 谱线位置/幅值与解析解吻合(tol=%g) + 逆变换还原 + "
           "多线程结果与单线程逐点一致\n", TOL);
    return 0;
}
