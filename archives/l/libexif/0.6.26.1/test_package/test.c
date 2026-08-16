#include <stdio.h>
#include <stdlib.h>
#include <libexif/exif-data.h>
#include <libexif/exif-loader.h>

int main(void) {
    /* R34: test 必须实质调用被测包 API，禁止空壳测试 */
    ExifData *data = exif_data_new();
    if (!data) {
        printf("libexif 0.6.26.1: exif_data_new() returned NULL\n");
        return 1;
    }

    ExifLoader *loader = exif_loader_new();
    if (!loader) {
        printf("libexif 0.6.26.1: exif_loader_new() returned NULL\n");
        exif_data_unref(data);
        return 1;
    }

    /* 验证 API 可正常创建与释放（内存管理路径） */
    exif_loader_unref(loader);
    exif_data_unref(data);
    printf("test libexif 0.6.26.1: OK\n");
    return 0;
}
