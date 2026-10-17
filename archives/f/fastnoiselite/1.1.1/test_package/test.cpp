// test_package: 消费者视角验证 fastnoiselite 1.1.1
// 仅通过公开头文件 <FastNoiseLite.h> 与公开 API 使用该库，
// 验证第三方使用者可以编译、链接并实际运行噪声生成。
#include <cstdio>
#include <cmath>
#include <array>
#include "FastNoiseLite.h"

int main() {
    // 显式构造 FastNoiseLite 实例（公开构造函数 + SetSeed）
    FastNoiseLite noise(1337);
    noise.SetNoiseType(FastNoiseLite::NoiseType_Perlin);
    noise.SetSeed(42);

    // 调用公开 API 生成 2D/3D 噪声并验证结果
    std::array<float, 8> vals2d{};
    for (int i = 0; i < 8; ++i) {
        float v = noise.GetNoise(static_cast<float>(i) * 0.5f, 3.25f);
        vals2d[i] = v;
        if (!std::isfinite(v) || v < -1.0001f || v > 1.0001f) {
            std::fprintf(stderr, "FAIL: GetNoise(2D) out of range: %f\n", v);
            return 1;
        }
    }
    float v3d = noise.GetNoise(1.0f, 2.0f, 3.0f);
    if (!std::isfinite(v3d) || v3d < -1.0001f || v3d > 1.0001f) {
        std::fprintf(stderr, "FAIL: GetNoise(3D) out of range: %f\n", v3d);
        return 1;
    }

    // 确定性验证：相同 seed 与坐标应得到相同结果
    FastNoiseLite noise2(1337);
    noise2.SetNoiseType(FastNoiseLite::NoiseType_Perlin);
    noise2.SetSeed(42);
    float ref = noise2.GetNoise(0.0f, 0.0f);
    float same = noise.GetNoise(0.0f, 0.0f);
    if (ref != same) {
        std::fprintf(stderr, "FAIL: deterministic check mismatch: %f vs %f\n", ref, same);
        return 1;
    }

    std::printf("test fastnoiselite 1.1.1: OK (perlin 2D/3D in-range, deterministic; sample=%f, %f)\n",
                vals2d[1], v3d);
    return 0;
}