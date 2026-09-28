/*
 * test_consumer.cpp — libspatialaudio 消费者用例
 *
 * 仅通过库已安装/导出的公开头文件、公开 API 与正常链接目标使用该库，
 * 验证第三方业务组件能否编译、链接、调用并正常运行。
 * 调用公开 API：spaudio::AmbisonicEncoder / spaudio::BFormat
 */
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>

#include <spatialaudio/AmbisonicEncoder.h>
#include <spatialaudio/BFormat.h>

int main() {
    // —— 业务意义公开 API 调用 1：一阶 Ambisonic 编码 ——
    constexpr unsigned nSamples = 512;
    constexpr unsigned order = 1;          // 一阶 HOA（W X Y Z）
    constexpr unsigned nChannels = (order + 1) * (order + 1);

    spaudio::AmbisonicEncoder encoder;
    bool ok = encoder.Configure(order, true /*b3D*/, 48000 /*sampleRate*/, 0.f /*fade*/);
    assert(ok && "AmbisonicEncoder::Configure failed");
    if (!ok) {
        std::fprintf(stderr, "FAIL: AmbisonicEncoder::Configure returned false\n");
        return 1;
    }
    // 设置声源方位并刷新编码系数（公开 API：SetPosition + Refresh）
    encoder.SetPosition(spaudio::PolarPosition<float>{90.f, 0.f, 1.f});
    encoder.Refresh();

    spaudio::BFormat bf;
    ok = bf.Configure(order, true /*b3D*/, nSamples);
    assert(ok && "BFormat::Configure failed");
    if (!ok) {
        std::fprintf(stderr, "FAIL: BFormat::Configure returned false\n");
        return 1;
    }

    // 输入：0 号采样为 1.0 的脉冲，其余为 0
    float input[nSamples];
    std::memset(input, 0, sizeof(input));
    input[0] = 1.0f;

    encoder.Process(input, nSamples, &bf);

    // —— 可观察结果：W 声道能量必须非零（脉冲被编码进 W 声道）——
    float* w = bf.GetChannelPointer(0);
    bool wNonZero = false;
    for (unsigned i = 0; i < nSamples; ++i) {
        if (std::fabs(w[i]) > 1e-6f) {
            wNonZero = true;
            break;
        }
    }
    if (!wNonZero) {
        std::fprintf(stderr, "FAIL: encoded W channel is all-zero, impulse not encoded\n");
        return 1;
    }
    std::printf("OK: libspatialaudio consumer — AmbisonicEncoder+BFormat impulse "
                "encoded, W channel energy present (first sample=%f)\n",
                (double)w[0]);
    return 0;
}