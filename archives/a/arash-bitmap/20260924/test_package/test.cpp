#include <cstdio>
#include <cstdlib>
#include "bitmap_image.hpp"

int main(void) {
    // 消费者用例: 通过库安装的公共头文件创建 24-bit BMP, 写入像素, 保存为文件,
    // 再重新加载并校验尺寸与像素 —— 验证第三方使用者可编译、链接、调用并正常观察结果。
    const unsigned int w = 64, h = 48;
    bitmap_image image(w, h);
    if (!image) {
        printf("FAIL: bitmap_image(w,h) failed\n");
        return 1;
    }
    image.set_pixel(0, 0, 255, 0, 0);
    image.set_pixel(w - 1, h - 1, 0, 0, 255);
    image.save_image("test_consumer.bmp");
    bitmap_image loaded("test_consumer.bmp");
    if (!loaded) {
        printf("FAIL: reload test_consumer.bmp failed\n");
        return 1;
    }
    if (loaded.width() != w || loaded.height() != h) {
        printf("FAIL: dimension mismatch %ux%u != %ux%u\n", loaded.width(), loaded.height(), w, h);
        return 1;
    }
    rgb_t px;
    loaded.get_pixel(0, 0, px);
    if (px.red != 255 || px.green != 0 || px.blue != 0) {
        printf("FAIL: pixel(0,0) mismatch (%u,%u,%u)\n", px.red, px.green, px.blue);
        return 1;
    }
    printf("test arash-bitmap 20260924: OK (w=%u h=%u, pixel API + save/load verified)\n", loaded.width(), loaded.height());
    return 0;
}
