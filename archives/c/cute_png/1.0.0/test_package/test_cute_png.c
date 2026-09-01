/*
 * test_cute_png.c — 真实 PNG 解码 API 冒烟测试（鸿蒙平台消费者视角）。
 *
 * cute_png 1.0.0 对应上游 tinydeflate.h v1.0，其实现宏为 TINYDEFLATE_IMPL
 * （CUTE_PNG_IMPLEMENTATION 为改名后 master 版本的宏）。
 *   1. tdLoadPNGMem 解码一段合法的 1x1 红色 PNG → 成功，尺寸 1x1
 *   2. 校验像素值（RGBA 红色，允许 0x?F0000FF 各变体）
 * 全部通过打印 HMBS_TEST_PACKAGE_RESULT: PASS。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TINYDEFLATE_IMPL
#include "cute_png.h"

static int g_failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("  [PASS] %s\n", msg);                                   \
        } else {                                                            \
            printf("  [FAIL] %s\n", msg);                                   \
            g_failures++;                                                   \
        }                                                                   \
    } while (0)

/* 1x1 solid red PNG (RGBA non-interlaced). */
static const unsigned char g_1x1_red_png[] = {
    0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A, /* PNG signature */
    0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52, /* IHDR len+type */
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01, /* width=1 height=1 */
    0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53, /* bitdepth=8 color=RGB */
    0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41, /* IDAT len+type */
    0x54,0x78,0x9C,0x63,0xF8,0xCF,0xC0,0xF0, /* zlib: 1x1 red */
    0x1F,0x00,0x04,0x40,0x01,0x00,0x04,0x16, /* 0x01 0x01 */
    0x8F,0x90,0xE4,0x91,0x00,0x00,0x00,0x00, /* crc */
    0x49,0x45,0x4E,0x44,0xAE,0x42,0x60,0x82  /* IEND */
};

int main(void)
{
    printf("cute_png test_package smoke\n");

    tdImage img;
    memset(&img, 0, sizeof(img));

    img = tdLoadPNGMem(g_1x1_red_png, (int)sizeof(g_1x1_red_png));
    CHECK(img.pix != 0, "tdLoadPNGMem decodes 1x1 red PNG");
    CHECK(img.w == 1 && img.h == 1, "decoded image is 1x1");

    if (img.pix) {
        /* v1.0 tdImage: pix is tdPixel (r,g,b,a each uint8_t). */
        tdPixel px = img.pix[0];
        printf("  pixel RGBA = (%u,%u,%u,%u)\n",
               px.r, px.g, px.b, px.a);
        CHECK(px.r >= 0xF0 && px.g <= 0x0F && px.b <= 0x0F, "pixel is red");
        CHECK(px.a >= 0xF0, "alpha channel opaque");
        free(img.pix);
    }

    if (g_failures == 0) {
        printf("HMBS_TEST_PACKAGE_RESULT: PASS\n");
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d checks)\n", g_failures);
    return 1;
}
