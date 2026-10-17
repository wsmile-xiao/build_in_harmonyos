#include <libg15render.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int tests_run;
static int tests_failed;

static void check(int condition, const char *name)
{
    ++tests_run;
    if (!condition) {
        ++tests_failed;
        fprintf(stderr, "FAIL: %s\n", name);
    }
}

static int count_pixels(const g15canvas *canvas)
{
    int count = 0;
    unsigned int x;
    unsigned int y;
    for (y = 0; y < G15_LCD_HEIGHT; ++y) {
        for (x = 0; x < G15_LCD_WIDTH; ++x) {
            count += g15r_getPixel((g15canvas *)canvas, x, y);
        }
    }
    return count;
}

int main(int argc, char **argv)
{
    g15canvas canvas;
    short overlay[4] = {1, 0, 0, 1};
    unsigned char xbm[1] = {0x05};
    g15font *font;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <font-root>\n", argv[0]);
        return 2;
    }
    if (setenv("LIBG15RENDER_FONT_DIR", argv[1], 1) != 0) {
        perror("setenv");
        return 2;
    }

    memset(&canvas, 0xA5, sizeof(canvas));
    g15r_initCanvas(&canvas);
    check(count_pixels(&canvas) == 0 && canvas.mode_xor == 0 &&
              canvas.mode_reverse == 0 && canvas.mode_cache == 0,
          "canvas initialization");

    g15r_setPixel(&canvas, 10, 5, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 10, 5) == 1 &&
              g15r_getPixel(&canvas, G15_LCD_WIDTH, G15_LCD_HEIGHT) == 0,
          "pixel set get and bounds");

    g15r_clearScreen(&canvas, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 0, 0) == 1 &&
              g15r_getPixel(&canvas, G15_LCD_WIDTH - 1, G15_LCD_HEIGHT - 1) == 1,
          "screen clear black");

    g15r_clearScreen(&canvas, G15_COLOR_WHITE);
    canvas.mode_xor = 1;
    g15r_setPixel(&canvas, 2, 2, 1);
    g15r_setPixel(&canvas, 2, 2, 1);
    check(g15r_getPixel(&canvas, 2, 2) == 0, "xor drawing mode");

    canvas.mode_xor = 0;
    canvas.mode_reverse = 1;
    g15r_setPixel(&canvas, 3, 3, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 3, 3) == 0, "reverse drawing mode");

    g15r_initCanvas(&canvas);
    g15r_drawLine(&canvas, 1, 1, 8, 8, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 1, 1) == 1 &&
              g15r_getPixel(&canvas, 8, 8) == 1,
          "line rendering");

    g15r_initCanvas(&canvas);
    g15r_pixelBox(&canvas, 4, 4, 10, 10, G15_COLOR_BLACK, 1, 1);
    check(g15r_getPixel(&canvas, 4, 4) == 1 &&
              g15r_getPixel(&canvas, 7, 7) == 1,
          "filled box rendering");

    g15r_initCanvas(&canvas);
    g15r_drawCircle(&canvas, 20, 20, 5, 0, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 20, 15) == 1 &&
              g15r_getPixel(&canvas, 20, 25) == 1,
          "circle rendering");

    g15r_initCanvas(&canvas);
    g15r_drawRoundBox(&canvas, 30, 5, 50, 20, 1, G15_COLOR_BLACK);
    check(g15r_getPixel(&canvas, 40, 5) == 1 &&
              g15r_getPixel(&canvas, 40, 12) == 1,
          "rounded box rendering");

    g15r_initCanvas(&canvas);
    g15r_drawBar(&canvas, 1, 10, 100, 15, G15_COLOR_BLACK, 5, 10, 2);
    check(count_pixels(&canvas) > 0, "progress bar rendering");

    g15r_initCanvas(&canvas);
    g15r_pixelOverlay(&canvas, 60, 10, 2, 2, overlay);
    check(g15r_getPixel(&canvas, 60, 10) == 1 &&
              g15r_getPixel(&canvas, 61, 11) == 1,
          "pixel overlay rendering");

    g15r_initCanvas(&canvas);
    g15r_drawXBM(&canvas, xbm, 3, 1, 70, 10);
    check(g15r_getPixel(&canvas, 70, 10) == 1 &&
              g15r_getPixel(&canvas, 72, 10) == 1,
          "XBM rendering");

    font = g15r_requestG15DefaultFont(9);
    check(font != NULL && g15r_testG15FontWidth(font, "OHOS") > 0,
          "relocatable default font loading");

    g15r_initCanvas(&canvas);
    g15r_G15FPrint(&canvas, "HarmonyOS", 0, 10, 9, G15_JUSTIFY_LEFT,
                   G15_COLOR_BLACK, 0);
    check(count_pixels(&canvas) > 0, "bitmap font rendering");

    check(g15r_loadWbmpToBuf("/path/that/does/not/exist.wbmp", NULL, NULL) == NULL &&
              g15r_loadWbmpSplash(&canvas, "/path/that/does/not/exist.wbmp") == -1 &&
              g15r_ttfLoad(&canvas, "/path/that/does/not/exist.ttf", 10, 0) != 0,
          "invalid input failure paths");

    printf("HMBS_TEST_PACKAGE_RESULT(discovered=%d, executed=%d, passed=%d, "
           "failed=%d, skipped=0, suite=libg15render_api)\n",
           tests_run, tests_run, tests_run - tests_failed, tests_failed);
    return tests_failed == 0 ? 0 : 1;
}
