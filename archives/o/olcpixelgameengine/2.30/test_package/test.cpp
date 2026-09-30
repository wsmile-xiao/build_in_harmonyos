// 消费者用例：模拟业务上层组件/应用，仅通过库安装/导出的公开头文件
// olcPixelGameEngine.h 使用 olcPixelGameEngine 2.30，验证第三方使用者可
// 编译、链接、调用并正常运行（OHOS aarch64，无窗口环境）。
//
// OHOS 无上游原生窗口后端，按上游支持的无头模式（OLC_PGE_HEADLESS）消费，
// 调用有业务意义的公开 API 并输出可观察结果：
//   1) olc::Sprite 像素写入/读取回读
//   2) olc::PixelGameEngine::Construct 无头构造
//   3) olc::Pixel 颜色构造与常量比对
#include <cstdio>

#define OLC_PGE_HEADLESS
#define OLC_PGE_APPLICATION
#include "olcPixelGameEngine.h"

class OhosConsumerApp : public olc::PixelGameEngine
{
public:
    bool OnUserCreate() override { return true; }
    bool OnUserUpdate(float fElapsedTime) override { return true; }
};

int main()
{
    int failures = 0;

    // 公开 API 1: olc::Sprite 像素写入/读取（可观察结果）
    olc::Sprite spr(8, 8);
    spr.SetPixel(4, 4, olc::BLUE);
    olc::Pixel p = spr.GetPixel(4, 4);
    std::printf("CONSUMER sprite_pixel=0x%08X expected=0x%08X\n", p.n, olc::BLUE.n);
    if (p.n != olc::BLUE.n) failures++;

    // 公开 API 2: 无头模式下构造引擎（可观察结果）
    OhosConsumerApp app;
    olc::rcode rc = app.Construct(320, 240, 1, 1, false, false);
    std::printf("CONSUMER construct_rc=%d expected_ok=%d\n", static_cast<int>(rc),
                static_cast<int>(olc::rcode::OK));
    if (rc != olc::rcode::OK) failures++;

    // 公开 API 3: olc::Pixel 颜色构造与常量比对（可观察结果）
    olc::Pixel c(255, 0, 0, 255);
    std::printf("CONSUMER pixel_color=0x%08X expected=0x%08X\n", c.n, olc::RED.n);
    if (c.n != olc::RED.n) failures++;

    std::printf("CONSUMER_RESULT failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
