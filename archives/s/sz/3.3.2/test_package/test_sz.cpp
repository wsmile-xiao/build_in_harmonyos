// SZ3 消费者测试（R34）：以库使用者身份调用公开 API 做压缩→解压闭环，
// 断言绝对误差界与压缩产物有效性；退出码 0=通过。
#include <cmath>
#include <cstdio>
#include <cstdlib>

#include <SZ3/api/sz.hpp>

int main() {
    // 3D 科学数据场 64x64x16 = 65536 个 float
    const size_t D1 = 64, D2 = 64, D3 = 16;
    const size_t N = D1 * D2 * D3;

    SZ3::Config conf(D1, D2, D3);
    conf.errorBoundMode = SZ3::EB_ABS;
    conf.absErrorBound = 0.1;  // 数据幅值 ~100，绝对误差界 0.1

    float *data = new float[N];
    for (size_t i = 0; i < N; i++) {
        data[i] = static_cast<float>(std::sin(i * 0.01) * 100.0 +
                                     std::cos(i * 0.031) * 10.0);
    }

    // 压缩（zstd 无损失后级经 INTERFACE 依赖链接）
    size_t cmpSize = 0;
    char *cmpData = SZ_compress<float>(conf, data, cmpSize);
    if (cmpData == nullptr || cmpSize == 0) {
        std::fprintf(stderr, "FAIL: SZ_compress returned empty result\n");
        delete[] data;
        return 1;
    }

    // 解压
    float *decData = SZ_decompress<float>(conf, cmpData, cmpSize);
    if (decData == nullptr) {
        std::fprintf(stderr, "FAIL: SZ_decompress returned null\n");
        delete[] data;
        delete[] cmpData;
        return 1;
    }

    // 断言：最大绝对误差不超过声明的误差界
    double maxErr = 0.0;
    for (size_t i = 0; i < N; i++) {
        double e = std::fabs(static_cast<double>(data[i]) - static_cast<double>(decData[i]));
        if (e > maxErr) maxErr = e;
    }

    std::printf("N=%zu cmpSize=%zu (%.2f%% of raw) maxAbsErr=%.6g (bound=%g)\n",
                N, cmpSize, 100.0 * cmpSize / (N * sizeof(float)), maxErr,
                conf.absErrorBound);

    int rc = 0;
    if (maxErr > static_cast<double>(conf.absErrorBound)) {
        std::fprintf(stderr, "FAIL: max abs error %.6g exceeds bound %g\n",
                     maxErr, conf.absErrorBound);
        rc = 1;
    } else {
        std::printf("SZ3 consumer test PASSED\n");
    }

    delete[] data;
    delete[] cmpData;
    delete[] decData;
    return rc;
}
