#include <stdio.h>
#include <stdlib.h>
#include "gd.h"

int main(void) {
    gdImagePtr im;
    int red, green, blue;
    const char *ver = gdVersionString();
    if (ver == NULL || ver[0] == '\0') {
        fprintf(stderr, "gdVersionString() returned empty\n");
        return 1;
    }
    /* 真实调用 GD API：创建真彩色图像并绘制 */
    im = gdImageCreateTrueColor(64, 64);
    if (im == NULL) {
        fprintf(stderr, "gdImageCreateTrueColor failed\n");
        return 1;
    }
    red = gdImageColorAllocate(im, 255, 0, 0);
    green = gdImageColorAllocate(im, 0, 255, 0);
    blue = gdImageColorAllocate(im, 0, 0, 255);
    gdImageFilledRectangle(im, 0, 0, 63, 63, red);
    gdImageLine(im, 0, 0, 63, 63, green);
    gdImageLine(im, 0, 63, 63, 0, blue);
    gdImageDestroy(im);
    printf("test gd %s: OK\n", ver);
    return 0;
}
