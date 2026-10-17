/* test_package/test.cpp — fftwpp 3.03 消费者测试
 *
 * 上游 example0.cc 的收敛版：ComplexAlign 分配 1D 数组，fft1d 前向 FFT
 * → 校验解析谱 → fftNormalized 反变换还原。断言带数值容差，非空壳测试。
 *
 * 关键接线点：
 *   - #include <fftwpp/fftw++.h>（头文件由本包 include/fftwpp/ 提供）
 *   - 链接 fftwpp 伴随编译单元 fftw++.cc / parallel.cc（包内 src/）
 *   - 底层 FFTW3 由 fftw/3.3.10 提供（-lfftw3）
 *   - 单线程模式（FFTWPP_SINGLE_THREAD），与仓内 fftw 3.3.10 串行版对齐
 *
 * OHOS 适配要点（实测证据，notes.md 有完整链路）：
 *   fftw/3.3.10-OHOS 在「WISDOM_ONLY 计划失败后 forget_wisdom 再计时计划」
 *   路径死锁（FFTW_MEASURE 计时源问题，3.3.10.1 配方已确认此症并改 CMake 修）。
 *   fftwpp 默认 fftw::effort=FFTW_MEASURE 且 Planner() 强制走 WISDOM_ONLY 链，
 *   会稳定踩中该死锁。消费者侧设置 fftw::effort=FFTW_ESTIMATE 即完全避让
 *   （实测 ctor+fft+fftNormalized 2 秒内全绿）。
 */
#include <fftwpp/fftw++.h>

#include <cmath>
#include <cstdio>
#include <cstddef>

using namespace utils;
using namespace fftwpp;
using namespace parallel;

static int g_failed = 0, g_total = 0;
static void check(bool ok, const char *what, const char *detail) {
    g_total++;
    std::printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
                (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

int main() {
    /* OHOS 适配：ESTIMATE 避开 fftw/3.3.10 的 MEASURE 计时死锁（见文件头） */
    fftw::effort = FFTW_ESTIMATE;

    /* 单线程模式下 get_max_threads() 返回 1（parallel.h SINGLE_THREAD） */
    fftw::maxthreads = get_max_threads();
    check(fftw::maxthreads == 1,
          "FFTWPP_SINGLE_THREAD 生效（maxthreads==1）", NULL);

    const size_t n = 4;
    Complex *f = ComplexAlign(n);

    /* 输入：f[i] = i（example0.cc 原始设定） */
    for (size_t i = 0; i < n; i++) f[i] = Complex(static_cast<double>(i), 0.0);

    fft1d Forward(n, -1);
    fft1d Backward(n, 1);

    Forward.fft(f);

    /* f[i]=i (n=4) 的 DFT 解析解（w = exp(-i*pi/2) = -i）：
     *   X[k] = 0 + 1*w^k + 2*w^{2k} + 3*w^{3k}
     *   X[0] = 6,  X[1] = -2+2i,  X[2] = -2,  X[3] = -2-2i
     */
    char buf[256];
    double r0 = f[0].real(), i0 = f[0].imag();
    double r1 = f[1].real(), i1 = f[1].imag();
    double r2 = f[2].real(), i2 = f[2].imag();
    double r3 = f[3].real(), i3 = f[3].imag();
    std::snprintf(buf, sizeof(buf),
                  "X0=(%g,%g) X1=(%g,%g) X2=(%g,%g) X3=(%g,%g) "
                  "期望 (6,0)(-2,2)(-2,0)(-2,-2)",
                  r0, i0, r1, i1, r2, i2, r3, i3);
    bool ok_fft = std::fabs(r0 - 6.0) < 1e-9 && std::fabs(i0) < 1e-9 &&
                  std::fabs(r1 + 2.0) < 1e-9 && std::fabs(i1 - 2.0) < 1e-9 &&
                  std::fabs(r2 + 2.0) < 1e-9 && std::fabs(i2) < 1e-9 &&
                  std::fabs(r3 + 2.0) < 1e-9 && std::fabs(i3 + 2.0) < 1e-9;
    check(ok_fft, "1D 前向 FFT 数值正确（f[i]=i 的解析谱）", buf);

    Backward.fftNormalized(f);

    /* 归一化反变换应精确还原 f[i] = i */
    double maxerr = 0.0;
    for (size_t i = 0; i < n; i++) {
        double e = std::fabs(f[i].real() - static_cast<double>(i)) +
                   std::fabs(f[i].imag());
        if (e > maxerr) maxerr = e;
    }
    std::snprintf(buf, sizeof(buf), "max |err| = %.3e", maxerr);
    check(maxerr < 1e-9, "fftNormalized 反变换还原输入", buf);

    deleteAlign(f);

    std::printf("\nfftwpp 3.03 smoke: %d/%d assertions passed\n",
                g_total - g_failed, g_total);
    return g_failed == 0 ? 0 : 1;
}
