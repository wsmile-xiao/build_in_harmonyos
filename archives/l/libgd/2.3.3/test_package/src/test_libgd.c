// R34: 实质调用 libgd API — 真彩色图像创建 + PNG 编码
#include <stdio.h>
#include <gd.h>

int main(void) {
    /* 创建 10x10 真彩色图像（libgd 核心 API） */
    gdImagePtr im = gdImageCreateTrueColor(10, 10);
    if (im == NULL) {
        fprintf(stderr, "FAIL: gdImageCreateTrueColor 返回 NULL\n");
        return 1;
    }
    int white = gdImageColorAllocate(im, 255, 255, 255);
    gdImageFilledRectangle(im, 0, 0, 9, 9, white);
    /* 编码 PNG 到内存（验证 libpng + zlib 依赖链） */
    int sz = 0;
    void *png_data = gdImagePngPtr(im, &sz);
    if (png_data == NULL || sz <= 0) {
        fprintf(stderr, "FAIL: gdImagePngPtr 失败（PNG 编码——libpng/zlib 依赖链）\n");
        gdImageDestroy(im);
        return 1;
    }
    gdFree(png_data);
    gdImageDestroy(im);
    printf("PASS: libgd API 调用成功（真彩色图像 + PNG 编码 %d 字节）\n", sz);
    return 0;
}
