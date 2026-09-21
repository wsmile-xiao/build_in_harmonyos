#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "svpng.inc"

/* 消费者验证：调用公开 API svpng() 生成一张 32x32 RGBA PNG，
 * 校验输出文件存在、PNG 签名正确且大小合理（非空壳测试）。 */
int main(void) {
    const unsigned w = 32, h = 32;
    unsigned char rgba[w * h * 4], *p = rgba;
    unsigned x, y;
    unsigned char sig[8] = {0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
    unsigned char head[8] = {0};
    FILE *fp;
    long size;

    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++) {
            *p++ = (unsigned char)(x * 8);      /* R */
            *p++ = (unsigned char)(y * 8);      /* G */
            *p++ = 128;                         /* B */
            *p++ = (unsigned char)((x + y) * 4);/* A */
        }

    fp = fopen("consumer.png", "wb");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot open consumer.png\n");
        return 1;
    }
    svpng(fp, w, h, rgba, 1);
    fclose(fp);

    fp = fopen("consumer.png", "rb");
    if (!fp) {
        fprintf(stderr, "FAIL: consumer.png not produced\n");
        return 1;
    }
    if (fread(head, 1, 8, fp) != 8) {
        fprintf(stderr, "FAIL: consumer.png too short\n");
        fclose(fp);
        return 1;
    }
    fseek(fp, 0, SEEK_END);
    size = ftell(fp);
    fclose(fp);

    if (memcmp(head, sig, 8) != 0) {
        fprintf(stderr, "FAIL: consumer.png has wrong PNG signature\n");
        return 1;
    }
    if (size < 64) {
        fprintf(stderr, "FAIL: consumer.png implausibly small (%ld bytes)\n", size);
        return 1;
    }
    printf("PASS: svpng() produced valid PNG (%ld bytes)\n", size);
    return 0;
}
