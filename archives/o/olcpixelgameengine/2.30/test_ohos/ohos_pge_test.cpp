// HarmonyOS PC 专项测试 — olcPixelGameEngine 2.30
// OHOS aarch64 上对 OLC_PGE_HEADLESS 无头模式做独立专项验证，
// 区别于 test_package 消费者用例：直接以 OHOS 工具链编译运行，
// 覆盖更多公开 API 的可观察结果：
//   1) olc::Sprite 像素填充/采样（64x64 渐变图案）
//   2) olc::Sprite::GetPixel 采样
//   3) olc::PixelGameEngine::Construct 无头构造
//   4) olc::vi2d 向量运算
//   5) olc::Pixel 颜色常量比对
#include <cstdio>

#define OLC_PGE_HEADLESS
#define OLC_PGE_APPLICATION
#include "olcPixelGameEngine.h"

class OhosTestApp : public olc::PixelGameEngine
{
public:
    bool OnUserCreate() override { return true; }
    bool OnUserUpdate(float fElapsedTime) override { return true; }
};

int main()
{
    int failures = 0;

    // 1) Sprite 64x64 渐变填充 + 采样
    olc::Sprite spr(64, 64);
    for (int y = 0; y < 64; y++)
        for (int x = 0; x < 64; x++)
            spr.SetPixel(x, y, olc::Pixel((uint8_t)x * 4, (uint8_t)y * 4, 255, 255));
    olc::Pixel p0 = spr.GetPixel(0, 0);
    olc::Pixel p63 = spr.GetPixel(63, 63);
    std::printf("OHOS_TEST sprite(0,0)=0x%08X sprite(63,63)=0x%08X\n", p0.n, p63.n);
    if (p0.r != 0 || p0.g != 0 || p63.r != 252 || p63.g != 252) failures++;

    // 2) Sprite::GetPixel 采样（公开 API，确定性结果）
    olc::Pixel ps = spr.GetPixel(10, 20);
    std::printf("OHOS_TEST sample(10,20)=0x%08X expected=0x%08X\n", ps.n, olc::Pixel(40, 80, 255, 255).n);
    if (ps.r != 40 || ps.g != 80) failures++;

    // 3) 无头引擎构造
    OhosTestApp app;
    olc::rcode rc = app.Construct(640, 480, 1, 1, false, false);
    std::printf("OHOS_TEST construct_rc=%d expected_ok=%d\n", static_cast<int>(rc),
                static_cast<int>(olc::rcode::OK));
    if (rc != olc::rcode::OK) failures++;

    // 4) vi2d 向量运算
    olc::vi2d v(3, 4);
    olc::vi2d w = v + olc::vi2d(1, 1);
    std::printf("OHOS_TEST vi2d=(%d,%d) expected=(4,5)\n", w.x, w.y);
    if (w.x != 4 || w.y != 5) failures++;

    // 5) Pixel 常量比对
    olc::Pixel c(255, 0, 0, 255);
    std::printf("OHOS_TEST pixel=0x%08X expected=0x%08X\n", c.n, olc::RED.n);
    if (c.n != olc::RED.n) failures++;

    std::printf("OHOS_TEST_RESULT failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
