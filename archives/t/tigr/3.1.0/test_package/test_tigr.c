/*
 * test_tigr.c — tigr 3.1.0 消费者测试（TIGR_HEADLESS 模式）
 *
 * 仅通过库公开头文件 <tigr.h> 与公开 API 使用库：
 *   tigrBitmap / tigrClear / tigrFillRect / tigrCircle / tigrPrint /
 *   tigrSaveImage / tigrLoadImage / tigrGet / tigrFree / tigrTextWidth
 *
 * 流程：创建 320x240 位图 → 填充背景 → 绘制矩形/圆 → 渲染文字 →
 * 保存 PNG → 重新加载 PNG → 校验尺寸与像素内容（可观察结果）。
 * 全部为纯 framebuffer 操作，无窗口/显示依赖。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tigr.h"

#define W 320
#define H 240

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

int main(void) {
    const char *png_path = "tigr-test-out.png";

    /* 1. 创建离屏位图 */
    Tigr *bmp = tigrBitmap(W, H);
    check(bmp != NULL, "tigrBitmap(320,240) returns non-NULL");
    if (!bmp) return 1;
    check(bmp->w == W && bmp->h == H, "bitmap dimensions 320x240");

    /* 2. 填充背景色（深蓝灰） */
    tigrClear(bmp, tigrRGB(0x80, 0x90, 0xa0));
    check(tigrGet(bmp, 0, 0).r == 0x80, "pixel(0,0).r == 0x80 after clear");
    check(tigrGet(bmp, 0, 0).b == 0xa0, "pixel(0,0).b == 0xa0 after clear");

    /* 3. 绘制矩形（红色边框） */
    tigrRect(bmp, 10, 10, 100, 50, tigrRGB(0xff, 0x00, 0x00));
    check(tigrGet(bmp, 10, 10).r == 0xff && tigrGet(bmp, 10, 10).g == 0,
          "rect border pixel is red");

    /* 4. 实心圆（绿色） */
    tigrFillCircle(bmp, 160, 120, 30, tigrRGB(0x00, 0xff, 0x00));
    TPixel c = tigrGet(bmp, 160, 120);
    check(c.g == 0xff, "circle center pixel is green");

    /* 5. 渲染文字（白色，bitmap 字体） */
    const char *msg = "Hello tigr on OHOS";
    int tw = tigrTextWidth(tfont, msg);
    check(tw > 0, "tigrTextWidth returns positive width");
    tigrPrint(bmp, tfont, 30, 150, tigrRGB(0xff, 0xff, 0xff), msg);
    check(tigrGet(bmp, 30, 150).r == 0xff, "text pixel is white");

    /* 6. 保存 PNG */
    check(tigrSaveImage(png_path, bmp) == 1, "tigrSaveImage returns 1 (success)");
    FILE *f = fopen(png_path, "rb");
    check(f != NULL, "PNG file exists on disk");
    if (f) {
        unsigned char sig[8];
        size_t n = fread(sig, 1, 8, f);
        fclose(f);
        check(n == 8 && sig[0] == 0x89 && sig[1] == 'P' && sig[2] == 'N' &&
                  sig[3] == 'G',
              "PNG signature valid");
    }

    /* 7. 重新加载 PNG 并校验内容 */
    Tigr *loaded = tigrLoadImage(png_path);
    check(loaded != NULL, "tigrLoadImage returns non-NULL");
    if (loaded) {
        check(loaded->w == W && loaded->h == H, "reloaded PNG size 320x240");
        TPixel lc = tigrGet(loaded, 160, 120);
        check(lc.g == 0xff, "reloaded circle center still green");
        tigrFree(loaded);
    }

    /* 8. 释放位图 */
    tigrFree(bmp);
    check(failures == 0, "all checks passed");

    if (failures) {
        fprintf(stderr, "%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("ALL %d CHECKS PASSED\n", passes);
    return 0;
}
