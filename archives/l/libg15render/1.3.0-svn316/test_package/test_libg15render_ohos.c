#include <libg15render.h>

#include <stdint.h>
#include <stdio.h>

#ifndef __OHOS__
#error "This test must be compiled for HarmonyOS/OHOS"
#endif

#ifndef __aarch64__
#error "This test must target AArch64"
#endif

int main(void)
{
    int passed = 0;
    g15canvas canvas;

    if (sizeof(void *) == 8 && sizeof(uintptr_t) == 8) {
        ++passed;
    }
    if (G15_LCD_WIDTH == 160 && G15_LCD_HEIGHT == 43 && G15_BUFFER_LEN == 1048) {
        ++passed;
    }
    g15r_initCanvas(&canvas);
    g15r_setPixel(&canvas, G15_LCD_WIDTH - 1, G15_LCD_HEIGHT - 1,
                  G15_COLOR_BLACK);
    if (g15r_getPixel(&canvas, G15_LCD_WIDTH - 1, G15_LCD_HEIGHT - 1) == 1) {
        ++passed;
    }

    printf("HMBS_TEST_PACKAGE_RESULT(discovered=3, executed=3, passed=%d, "
           "failed=%d, skipped=0, suite=libg15render_ohos)\n",
           passed, 3 - passed);
    return passed == 3 ? 0 : 1;
}
