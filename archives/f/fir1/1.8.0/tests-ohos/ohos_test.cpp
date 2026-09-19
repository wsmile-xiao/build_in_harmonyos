// OHOS 专项测试：通过公开 API 验证 fir1 在 HarmonyOS PC (armv8, OHOS clang)
// 平台上的完整功能与可观察结果（与上游 ctest 6 项、test_package 消费者用例
// 分别计数）。
//
// 验证点：
//   1. 系数数组/向量构造 + getTaps
//   2. 冲激响应复现系数（delta 输入 -> 逐拍输出等于系数）
//   3. 步进响应累积（unit step -> 输出等于系数累积和）
//   4. LMS 自适应对消收敛（正弦 vs 余弦，稳态残差 < 1E-5）
//   5. getCoeff / getCoeffVector 回读一致性与零填充
//   6. 文件构造（coefficients.dat 读取）
#include "Fir1.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "OHOS test FAILED: %s (line %d)\n", msg, __LINE__); \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(int, char**) {
    // 1. 数组构造 + getTaps
    const double c[] = {1, 3, 2, -5, 8, -8, 7, 9};
    Fir1 fir(c);
    CHECK(fir.getTaps() == 8, "array ctor getTaps==8");

    // 2. 冲激响应：delta 在 t=1，输出逐拍等于系数
    double v = 0;
    for (int i = 0; i < 9; i++) {
        v = fir.filter(i == 1 ? 1.0 : 0.0);
        if (i > 0) {
            CHECK(round(c[i - 1]) == round(v), "impulse response reproduces coeffs");
        }
    }

    // 3. 步进响应累积
    Fir1 fir2(c);
    double acc = 0;
    for (int i = 0; i < 16; i++) {
        double vin = 0;
        if (i > 10) {
            vin = 1;
        }
        v = fir2.filter(vin);
        if (i > 10) {
            acc += c[i - 11];
            CHECK(round(v) == round(acc), "step response accumulates");
        }
    }

    // 4. LMS 自适应对消（余弦信号被正弦参考对消）
    Fir1 lmsFir(10);
    CHECK(lmsFir.getTaps() == 10, "lms ctor getTaps==10");
    lmsFir.setLearningRate(0.1);
    double output_signal = 0;
    for (int i = 0; i < 100; i++) {
        double input_signal = cos(2 * M_PI / 20 * i) * 0.1;
        double ref_noise = sin(2 * M_PI / 20 * i);
        double canceller = lmsFir.filter(ref_noise);
        output_signal = input_signal - canceller;
        lmsFir.lms_update(output_signal);
    }
    CHECK(fabs(output_signal) < 1E-5, "LMS cancelled sine with cosine");

    // 5. getCoeff / getCoeffVector 回读一致性与零填充
    double w[10];
    for (int i = 0; i < 10; i++) {
        w[i] = (double)rand() / RAND_MAX;
    }
    Fir1 fir3(w, 10);
    double w_out[12];
    fir3.getCoeff(w_out, 10);
    for (int i = 0; i < 10; i++) {
        CHECK(w_out[i] == w[i], "getCoeff round-trip");
    }
    w_out[10] = w_out[11] = 1.0;
    fir3.getCoeff(w_out, 12);
    CHECK(w_out[10] == 0 && w_out[11] == 0, "getCoeff zero-padding");

    std::vector<double> wv(w, w + 10);
    Fir1 fir4(wv);
    std::vector<double> wv_out = fir4.getCoeffVector();
    CHECK(wv_out.size() == 10, "getCoeffVector size");
    for (int i = 0; i < 10; i++) {
        CHECK(wv_out[i] == wv[i], "getCoeffVector round-trip");
    }

    // 6. 文件构造（coefficients.dat 相对路径，需在工作目录运行）
    Fir1 fir5("coefficients.dat");
    fir5.reset();
    FILE* f = fopen("coefficients.dat", "rt");
    CHECK(f != NULL, "coefficients.dat readable");
    double expected;
    for (int i = 0; i < 30; i++) {
        float a = 0;
        if (i == 10) {
            a = 1;
        }
        double b = fir5.filter(a);
        if (i >= 10) {
            CHECK(fscanf(f, "%lf\n", &expected) > 0, "coefficient read");
            CHECK(expected == b, "file ctor filter output matches file");
        }
    }
    fclose(f);

    printf("OHOS test PASSED (fir1 1.8.0, impulse/step/LMS/getCoeff/file)\n");
    return 0;
}
