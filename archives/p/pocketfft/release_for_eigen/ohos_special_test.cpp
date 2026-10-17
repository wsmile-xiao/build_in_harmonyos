// HarmonyOS 专项测试：pocketfft release_for_eigen 真实消费入口验证
// 使用 OHOS armv8 工具链（clang 15 / aarch64-linux-ohos）实际编译并运行，
// 验证 header-only FFT 库在 OHOS 平台下的可编译性与运行时正确性。
// 覆盖：c2c 正反变换往返（默认多线程路径）、r2c/c2r 半复数变换、
//       大素数长度（Bluestein 算法路径，长度 1009）、float/double 双精度。
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstddef>
#include <vector>
#include "pocketfft_hdronly.h"

int main() {
    using namespace pocketfft;
    int failures = 0;

    // 1) c2c 往返：长度 16（常规 codelet 路径），多线程 nthreads=0（auto）
    {
        const size_t n = 16;
        shape_t shape{n};
        stride_t stride{sizeof(std::complex<double>)};
        std::vector<std::complex<double>> a(n), b(n);
        for (size_t i = 0; i < n; ++i)
            a[i] = std::complex<double>(i + 1.0, 2.0 * i - 0.5);
        c2c(shape, stride, stride, shape_t{0}, FORWARD, a.data(), b.data(), 1.0, 0);
        c2c(shape, stride, stride, shape_t{0}, BACKWARD, b.data(), a.data(), 1.0 / n, 0);
        double maxerr = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double er = std::abs(a[i] - std::complex<double>(i + 1.0, 2.0 * i - 0.5));
            if (er > maxerr) maxerr = er;
        }
        if (maxerr > 1e-10) { std::printf("FAIL: c2c roundtrip n=16 maxerr=%.3e\n", maxerr); failures++; }
    }

    // 2) r2c/c2r 半复数变换：长度 32，float 精度
    {
        const size_t n = 32;
        shape_t shape{n};
        stride_t stride{sizeof(float)};
        std::vector<float> x(n);
        for (size_t i = 0; i < n; ++i) x[i] = std::cos(2.0 * M_PI * 3.0 * i / n) + 0.5f * std::sin(2.0 * M_PI * 5.0 * i / n);
        // 半复数格式：长度为 n/2+1 的复数（含 Nyquist）
        std::vector<std::complex<float>> spec(n / 2 + 1);
        stride_t strided{sizeof(std::complex<float>)};
        r2c(shape, stride, strided, shape_t{0}, FORWARD, x.data(), spec.data(), 1.0f, 0);
        std::vector<float> y(n);
        c2r(shape, strided, stride, shape_t{0}, BACKWARD, spec.data(), y.data(), 1.0f / n, 0);
        float maxerr = 0.0f;
        for (size_t i = 0; i < n; ++i) {
            float er = std::fabs(y[i] - x[i]);
            if (er > maxerr) maxerr = er;
        }
        // 单精度容许 1e-3 容差
        if (maxerr > 1e-3f) { std::printf("FAIL: r2c/c2r roundtrip n=32 maxerr=%.3e\n", maxerr); failures++; }
    }

    // 3) 大素数长度（Bluestein 路径）：长度 1009（素数），double
    {
        const size_t n = 1009;
        shape_t shape{n};
        stride_t stride{sizeof(std::complex<double>)};
        std::vector<std::complex<double>> a(n), b(n);
        for (size_t i = 0; i < n; ++i)
            a[i] = std::complex<double>(std::sin(0.01 * i), std::cos(0.02 * i));
        c2c(shape, stride, stride, shape_t{0}, FORWARD, a.data(), b.data(), 1.0, 0);
        c2c(shape, stride, stride, shape_t{0}, BACKWARD, b.data(), a.data(), 1.0 / n, 0);
        double maxerr = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double er = std::abs(a[i] - std::complex<double>(std::sin(0.01 * i), std::cos(0.02 * i)));
            if (er > maxerr) maxerr = er;
        }
        if (maxerr > 1e-8) { std::printf("FAIL: Bluestein n=1009 roundtrip maxerr=%.3e\n", maxerr); failures++; }
    }

    if (failures == 0) {
        std::printf("pocketfft OHOS special test: PASSED (c2c/r2c/c2r/Bluestein, 3 scenarios)\n");
        return 0;
    }
    std::printf("pocketfft OHOS special test: FAILED (%d scenario(s))\n", failures);
    return 1;
}
