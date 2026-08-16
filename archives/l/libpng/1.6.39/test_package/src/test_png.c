// R34: 实质调用 libpng API — 创建/销毁读结构
#include <png.h>
#include <stdio.h>

int main(void) {
    /* png_create_read_struct：创建 libpng 读结构（核心 API——非空壳） */
    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING,
                                             NULL, NULL, NULL);
    if (png == NULL) {
        fprintf(stderr, "FAIL: png_create_read_struct 失败\n");
        return 1;
    }
    png_destroy_read_struct(&png, NULL, NULL);
    printf("PASS: libpng API 调用成功（png_create_read_struct）\n");
    return 0;
}
