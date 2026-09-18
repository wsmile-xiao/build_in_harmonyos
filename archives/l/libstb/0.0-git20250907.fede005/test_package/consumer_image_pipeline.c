/* consumer_image_pipeline.c — 消费者用例：模拟真实终端用户的图像处理管线
 *
 * 场景：程序内生成 16x16 RGB 四象限纯色图 → PNG 内存编码（stb_image_write）
 *      → PNG 内存解码（stb_image，无损回读）→ 2x 线性放大到 32x32
 *      （stb_image_resize2，新宏 STB_IMAGE_RESIZE2_IMPLEMENTATION）→ 校验。
 *
 * 断言设计：对纯色象限做 2x 放大时，距象限边界/图像边缘 ≥6px 的采样点
 * 不受滤波核跨越边界影响，值必等于原象限颜色（对任何正确实现的
 * 上采样滤波都成立，不依赖特定核）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_IMAGE_RESIZE2_IMPLEMENTATION
#include "stb_image_resize2.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        checks++;                                          \
        if (cond) {                                        \
            printf("PASS %s\n", msg);                      \
        } else {                                           \
            fprintf(stderr, "FAIL %s\n", msg);             \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    enum { W = 16, H = 16, C = 3, W2 = 32, H2 = 32 };
    /* 四象限纯色：TL=红 TR=绿 BL=蓝 BR=白 */
    static const unsigned char quad[4][3] = {
        {200, 30, 40}, {30, 180, 60}, {40, 60, 210}, {235, 235, 235},
    };
    unsigned char src[H * W * C];
    unsigned char *png = NULL, *dec = NULL, *big = NULL;
    int png_len = 0, w = 0, h = 0, n = 0;
    int x, y, qi;

    for (y = 0; y < H; y++) {
        for (x = 0; x < W; x++) {
            qi = (y >= H / 2) * 2 + (x >= W / 2);
            memcpy(&src[(y * W + x) * C], quad[qi], C);
        }
    }

    /* 1. PNG 内存编码 */
    png = stbi_write_png_to_mem(src, W * C, W, H, C, &png_len);
    CHECK(png != NULL && png_len > 0, "pipeline: stbi_write_png_to_mem 编码 16x16 PNG");
    if (!png)
        goto done;

    /* 2. PNG 内存解码（无损回读） */
    dec = stbi_load_from_memory(png, png_len, &w, &h, &n, 0);
    CHECK(dec != NULL && w == W && h == H && n == C, "pipeline: stbi_load_from_memory 解码尺寸/通道");
    if (dec) {
        CHECK(memcmp(src, dec, (size_t)(W * H * C)) == 0, "pipeline: 解码像素与源逐字节一致（PNG 无损）");

        /* 3. resize2 线性放大 2x（输出缓冲自分配） */
        big = stbir_resize_uint8_linear(dec, W, H, 0, NULL, W2, H2, 0, STBIR_RGB);
        CHECK(big != NULL, "pipeline: stbir_resize_uint8_linear 2x 放大（resize2）");
        if (big) {
            /* 4. 四象限内部采样点（各距边界≥6px）必等于原象限颜色 */
            static const int sx[4] = {8, 26, 8, 26};   /* TL TR BL BR 采样坐标 */
            static const int sy[4] = {8, 8, 26, 26};
            int ok = 1;
            for (qi = 0; qi < 4; qi++) {
                const unsigned char *px = &big[(sy[qi] * W2 + sx[qi]) * C];
                if (memcmp(px, quad[qi], C) != 0) {
                    fprintf(stderr, "  quadrant %d @( %d,%d ): got %d,%d,%d want %d,%d,%d\n",
                            qi, sx[qi], sy[qi], px[0], px[1], px[2],
                            quad[qi][0], quad[qi][1], quad[qi][2]);
                    ok = 0;
                }
            }
            CHECK(ok, "pipeline: 放大后四象限内部采样颜色正确");
        }
    }

done:
    free(big);
    stbi_image_free(dec);
    free(png);

    printf("\nconsumer pipeline checks: %d, failed: %d\n", checks, failures);
    if (failures == 0) {
        printf("consumer image pipeline: OK\n");
        return 0;
    }
    fprintf(stderr, "%d consumer check(s) FAILED\n", failures);
    return 1;
}
