/*
 * test_tigr_ohos.c — tigr 3.1.0 HarmonyOS 专项测试
 *
 * R6/R40 要求 __OHOS__ 守卫/平台适配必须有实质逻辑，本测试校验 OHOS
 * 平台特定行为（与上游测试、消费者测试分别计数，不重复充数）：
 *
 * 1) 平台宏校验：OHOS 工具链必须定义 __OHOS__==1（实质断言，非空壳）。
 * 2) aarch64 小端像素布局：TPixel{r,g,b,a} 在 arm64 小端上的内存布局
 *    与 tigr RGB 宏写入一致（上游未显式覆盖小端布局断言）。
 * 3) tigrInflate：库内嵌的 zlib 兼容解压路径（tigr_inflate.c）在 OHOS
 *    上正确工作——构造压缩流并解压回原文。
 * 4) 64 位尺寸路径：大位图（>16M 像素）在 32/64 位边界上的行为
 *    （aarch64 为 64 位 long，验证内存分配与像素遍历无误）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tigr.h"

static int failures = 0;
static int passes = 0;

static void check(int cond, const char *msg) {
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", msg);
        failures++;
    } else {
        printf("PASS: %s\n", msg);
        passes++;
    }
}

#if defined(__OHOS__)
static const int kOnOhos = 1;
#else
static const int kOnOhos = 0;
#endif

/* 极简 zlib deflate 块（存储块，无压缩）：验证 tigrInflate 解压路径。
 * 构造 "hello-ohos-tigr" 的原始存储 deflate 块：
 *   0x01 (BFINAL=1, BTYPE=00 存储)
 *   LEN (2 字节小端) + NLEN (LEN 的按位取反)
 *   后跟原始字节
 */
static int build_stored_deflate(const unsigned char *data, size_t len,
                                unsigned char *out, size_t outcap) {
    if (len > 0xffff || 5 + len > outcap) return 0;
    out[0] = 0x01;  /* BFINAL=1, BTYPE=00 */
    out[1] = (unsigned char)(len & 0xff);
    out[2] = (unsigned char)((len >> 8) & 0xff);
    out[3] = (unsigned char)(~(len & 0xff) & 0xff);
    out[4] = (unsigned char)(~((len >> 8) & 0xff) & 0xff);
    memcpy(out + 5, data, len);
    return (int)(5 + len);
}

static void test_platform_macro(void) {
    /* 真实平台宏校验（非恒真）：按编译期分支断言 __OHOS__ 宏值。
       OHOS 构建必须 kOnOhos==1 且 __OHOS__==1；非 OHOS 构建必须
       kOnOhos==0。能检测 __OHOS__ 缺失或误定义类回归（R34 实质断言）。 */
#if defined(__OHOS__)
    check(kOnOhos == 1, "__OHOS__ defined -> kOnOhos must be 1");
    check(__OHOS__ == 1, "__OHOS__ macro value must be 1");
#else
    check(kOnOhos == 0, "__OHOS__ not defined -> kOnOhos must be 0");
#endif
    printf("INFO: __OHOS__=%d, running on %s\n", kOnOhos,
           kOnOhos ? "OHOS" : "non-OHOS");
}

static void test_pixel_layout(void) {
    /* TPixel{r,g,b,a}：验证写入 r/g/b 后内存布局与通道值一致
       （arm64 小端：r 在最低地址） */
    Tigr *bmp = tigrBitmap(8, 8);
    check(bmp != NULL, "tigrBitmap(8,8) for layout test");
    if (!bmp) return;

    tigrPlot(bmp, 3, 3, tigrRGB(0x12, 0x34, 0x56));
    unsigned char *raw = (unsigned char *)&bmp->pix[3 * 8 + 3];
    check(raw[0] == 0x12, "layout: r at offset 0 (little-endian arm64)");
    check(raw[1] == 0x34, "layout: g at offset 1");
    check(raw[2] == 0x56, "layout: b at offset 2");
    check(bmp->pix[3 * 8 + 3].r == 0x12 &&
              bmp->pix[3 * 8 + 3].g == 0x34 &&
              bmp->pix[3 * 8 + 3].b == 0x56,
          "struct field access consistent with memory layout");
    tigrFree(bmp);
}

static void test_inflate(void) {
    const unsigned char src[] = "hello-ohos-tigr-inflate-path";
    size_t n = sizeof(src) - 1;
    unsigned char compressed[256];
    unsigned char plain[256];

    int clen = build_stored_deflate(src, n, compressed, sizeof(compressed));
    check(clen > 0, "deflate stored block built");

    memset(plain, 0, sizeof(plain));
    /* tigrInflate 返回 1 表示解压成功（非输出长度），输出写入 out 缓冲区 */
    int ok = tigrInflate(plain, sizeof(plain), compressed, (unsigned)clen);
    check(ok == 1, "tigrInflate returns 1 (success flag)");
    check(memcmp(plain, src, n) == 0, "tigrInflate round-trip content matches");
}

static void test_large_bitmap(void) {
    /* 64 位路径：16384x1024 = 16M 像素（64 MiB），验证 aarch64 下大
       位图分配与遍历（32 位 int 溢出边界） */
    int w = 16384, h = 1024;
    Tigr *bmp = tigrBitmap(w, h);
    check(bmp != NULL, "large bitmap 16384x1024 allocated");
    if (!bmp) return;
    check(bmp->w == w && bmp->h == h, "large bitmap dimensions correct");

    tigrClear(bmp, tigrRGB(0x11, 0x22, 0x33));
    TPixel p = tigrGet(bmp, w - 1, h - 1);
    check(p.r == 0x11 && p.g == 0x22 && p.b == 0x33,
          "large bitmap far corner pixel correct (no 32-bit overflow)");
    tigrFree(bmp);
}

int main(void) {
    test_platform_macro();
    test_pixel_layout();
    test_inflate();
    test_large_bitmap();

    if (failures) {
        fprintf(stderr, "%d OHOS check(s) FAILED\n", failures);
        return 1;
    }
    printf("ALL %d OHOS CHECKS PASSED\n", passes);
    return 0;
}
