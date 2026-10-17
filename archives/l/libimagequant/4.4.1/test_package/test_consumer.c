/* test_package/test_consumer.c — libimagequant 4.4.1 消费者 roundtrip 测试
 *
 * pngquant 同款用法（liq_attr → liq_image → liq_quantize → remap 全链路）：
 *   1. liq_attr_create + liq_set_max_colors
 *   2. liq_image_create_rgba（4x4 RGBA 渐变图）
 *   3. liq_quantize_image 得到 liq_result
 *   4. 调色板规模断言（1..max_colors）
 *   5. liq_set_dithering_level + liq_write_remapped_image
 *   6. 索引范围逐像素断言（remap roundtrip 完整性）
 *   7. 资源销毁顺序（result → image → attr）
 */
#include <stdio.h>
#include <stdlib.h>
#include "libimagequant.h"

int main(void) {
    const int w = 4, h = 4;
    unsigned char pixels[4 * 4 * 4];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            unsigned char *p = pixels + 4 * (y * w + x);
            p[0] = (unsigned char)(x * 80);
            p[1] = (unsigned char)(y * 80);
            p[2] = 128;
            p[3] = 255;
        }
    }

    /* 1. attr */
    liq_attr *attr = liq_attr_create();
    if (!attr) { fprintf(stderr, "FAIL: liq_attr_create\n"); return 1; }
    if (liq_set_max_colors(attr, 4) != LIQ_OK) {
        fprintf(stderr, "FAIL: liq_set_max_colors\n"); return 1;
    }

    /* 2. image */
    liq_image *img = liq_image_create_rgba(attr, pixels, w, h, 0);
    if (!img) { fprintf(stderr, "FAIL: liq_image_create_rgba\n"); return 1; }

    /* 3. quantize */
    liq_result *res = liq_quantize_image(attr, img);
    if (!res) { fprintf(stderr, "FAIL: liq_quantize_image\n"); return 1; }

    /* 4. palette assertions */
    const liq_palette *pal = liq_get_palette(res);
    if (!pal) { fprintf(stderr, "FAIL: liq_get_palette\n"); return 1; }
    if (pal->count < 1 || pal->count > 4) {
        fprintf(stderr, "FAIL: palette count %d out of range 1..4\n",
                (int)pal->count);
        return 1;
    }
    printf("palette entries: %d\n", (int)pal->count);

    /* 5. dither + remap */
    if (liq_set_dithering_level(res, 1.0) != LIQ_OK) {
        fprintf(stderr, "FAIL: liq_set_dithering_level\n"); return 1;
    }
    unsigned char *out = malloc((size_t)w * h);
    if (!out) { fprintf(stderr, "FAIL: alloc\n"); return 1; }
    if (liq_write_remapped_image(res, img, out, (size_t)w * h) != LIQ_OK) {
        fprintf(stderr, "FAIL: liq_write_remapped_image\n"); return 1;
    }

    /* 6. per-pixel index range assertion (roundtrip integrity) */
    for (int i = 0; i < w * h; i++) {
        if (out[i] >= pal->count) {
            fprintf(stderr, "FAIL: remap index %d >= palette size %d\n",
                    (int)out[i], (int)pal->count);
            return 1;
        }
    }
    printf("remap roundtrip OK (indices within palette)\n");

    /* 7. destroy in upstream documented order */
    liq_result_destroy(res);
    liq_image_destroy(img);
    liq_attr_destroy(attr);
    free(out);
    printf("consumer test PASS\n");
    return 0;
}
