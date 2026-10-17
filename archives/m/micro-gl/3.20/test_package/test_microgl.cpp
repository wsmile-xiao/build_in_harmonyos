/* test_microgl.cpp — 真实调用 micro-gl canvas API 的消费者测试。

在 OHOS aarch64 上创建 RGB888_PACKED_32 canvas：
1. clear 白色背景；
2. 用 flat_color 采样器绘制红色矩形；
3. 读回像素并断言矩形内为红、背景为白。

验证 micro-gl 的像素编码/解码与软件光栅化在 OHOS 平台实际可用。
*/
#include <microgl/canvas.h>
#include <microgl/bitmaps/bitmap.h>
#include <microgl/pixel_coders/RGB888_PACKED_32.h>
#include <microgl/samplers/flat_color.h>

#include <cstdio>

using namespace microgl;

int main() {
    const int W = 64, H = 64;
    uint32_t buffer[W * H] = {0};
    using Canvas24 = canvas<bitmap<coder::RGB888_PACKED_32>>;

    bitmap<coder::RGB888_PACKED_32> bmp(buffer, W, H);
    Canvas24 canvas(bmp);

    // 1) 白色背景
    canvas.clear(color_t{255, 255, 255, 255});

    // 2) 红色矩形 (10,10)-(30,30)
    sampling::flat_color<> red{{255, 0, 0, 255}};
    canvas.drawRect<blendmode::Normal, porterduff::FastSourceOverOnOpaque>(
        red, 10, 10, 30, 30);

    // 3) 读回像素断言
    const auto *pixels = canvas.bitmapCanvas().data();
    int failures = 0;

    // 矩形中心 (20,20) 应为红色。
    // microgl fast 预乘合成输出 = (src * 255) >> 8，255 色值会落到 254，
    // 因此断言 r >= 250 且 g/b == 0（验证红色填充与坐标映射，而非精确舍入）。
    color_t inside;
    coder::RGB888_PACKED_32::decode(pixels[20 * W + 20], inside);
    if (inside.r < 250 || inside.g != 0 || inside.b != 0) {
        std::printf("FAIL inside=(%d,%d,%d) expect red\n",
                    inside.r, inside.g, inside.b);
        failures++;
    }

    // 角落 (2,2) 应为白色背景
    color_t corner;
    coder::RGB888_PACKED_32::decode(pixels[2 * W + 2], corner);
    if (corner.r != 255 || corner.g != 255 || corner.b != 255) {
        std::printf("FAIL corner=(%d,%d,%d) expect white\n",
                    corner.r, corner.g, corner.b);
        failures++;
    }

    if (failures == 0) {
        std::printf("PASS microgl OHOS canvas render (2 checks)\n");
        return 0;
    }
    return 1;
}