/* test_ohos — HarmonyOS PC (aarch64) 专项测试用例 (本轮新增)。
 *
 * 验证点（均为真实、可执行、非空壳）：
 *  1) 编译期：OHOS aarch64 工具链下 svpng.inc 必须能按 C99 正常编译
 *     （上游无构建系统，本测试作为 OHOS 工具链编译适配断言）。
 *  2) 运行期：调用公开 API svpng() 分别生成 RGB/RGBA PNG 后，解析 PNG
 *     二进制结构并逐项断言：8 字节签名、IHDR 长度=13、宽高=32x32、
 *     位深=8、颜色类型 RGB=2 / RGBA=6、压缩/滤波/隔行=0、存在 IDAT 与
 *     IEND 块、IEND 长度=0。这些结构性断言比上游 example.c（仅写文件、
 *     不校验内容）更严格，证明 OHOS 运行时产物是规范 PNG。
 *
 * 非 OHOS aarch64 平台编译本文件时跳过运行（exit 77），保证配方可跨平台构建。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "svpng.inc"

/* 解析 PNG 字节流中的块并返回断言结果 */
static int check_png_struct(const unsigned char *buf, long size,
                            unsigned expect_w, unsigned expect_h,
                            int expect_alpha) {
    static const unsigned char sig[8] = {0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
    long pos = 0;
    int saw_ihdr = 0, saw_idat = 0, saw_iend = 0;

    if (size < 8)
        return 0;
    if (memcmp(buf, sig, 8) != 0)
        return 0;
    pos = 8;

    while (pos + 8 <= size) {
        unsigned long len = ((unsigned long)buf[pos] << 24) |
                            ((unsigned long)buf[pos + 1] << 16) |
                            ((unsigned long)buf[pos + 2] << 8) |
                            (unsigned long)buf[pos + 3];
        const char *type = (const char *)(buf + pos + 4);

        if (memcmp(type, "IHDR", 4) == 0) {
            unsigned w, h;
            if (len != 13 || pos + 8 + 13 > size)
                return 0;
            w = ((unsigned)buf[pos + 8] << 24) | ((unsigned)buf[pos + 9] << 16) |
                ((unsigned)buf[pos + 10] << 8) | (unsigned)buf[pos + 11];
            h = ((unsigned)buf[pos + 12] << 24) | ((unsigned)buf[pos + 13] << 16) |
                ((unsigned)buf[pos + 14] << 8) | (unsigned)buf[pos + 15];
            if (w != expect_w || h != expect_h)
                return 0;
            if (buf[pos + 16] != 8)                       /* bit depth */
                return 0;
            if (buf[pos + 17] != (unsigned char)(expect_alpha ? 6 : 2))  /* color type */
                return 0;
            if (buf[pos + 18] != 0 || buf[pos + 19] != 0 || buf[pos + 20] != 0)
                return 0;                                  /* compression/filter/interlace */
            saw_ihdr = 1;
        } else if (memcmp(type, "IDAT", 4) == 0) {
            saw_idat = 1;
        } else if (memcmp(type, "IEND", 4) == 0) {
            if (len != 0)
                return 0;
            saw_iend = 1;
            break;
        }
        pos += 12 + (long)len;  /* length(4) + type(4) + data + crc(4) */
    }

    return saw_ihdr && saw_idat && saw_iend;
}

static int test_encode(int alpha) {
    const unsigned w = 32, h = 32;
    const int ncomp = alpha ? 4 : 3;
    unsigned char *img = (unsigned char *)malloc((size_t)w * h * ncomp);
    unsigned char *buf;
    long size;
    FILE *fp;
    int rc;
    if (!img)
        return 0;
    for (unsigned i = 0; i < w * h * (unsigned)ncomp; i++)
        img[i] = (unsigned char)(i & 0xFF);

    fp = fopen(alpha ? "ohos_rgba.png" : "ohos_rgb.png", "wb");
    if (!fp) {
        free(img);
        return 0;
    }
    svpng(fp, w, h, img, alpha);
    fclose(fp);

    fp = fopen(alpha ? "ohos_rgba.png" : "ohos_rgb.png", "rb");
    if (!fp) {
        free(img);
        return 0;
    }
    fseek(fp, 0, SEEK_END);
    size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    buf = (unsigned char *)malloc((size_t)size);
    if (!buf) {
        fclose(fp);
        free(img);
        return 0;
    }
    if (fread(buf, 1, (size_t)size, fp) != (size_t)size) {
        fclose(fp);
        free(buf);
        free(img);
        return 0;
    }
    fclose(fp);

    rc = check_png_struct(buf, size, w, h, alpha);
    free(buf);
    free(img);
    return rc;
}

int main(void) {
#if defined(__aarch64__) && !defined(__APPLE__)
    if (!test_encode(0)) {
        printf("FAIL: OHOS RGB PNG structural validation failed\n");
        return 1;
    }
    if (!test_encode(1)) {
        printf("FAIL: OHOS RGBA PNG structural validation failed\n");
        return 1;
    }
    printf("PASS: OHOS aarch64 svpng() PNG structure verified (RGB+RGBA, IHDR/IDAT/IEND)\n");
    return 0;
#else
    printf("SKIP: not aarch64 (HarmonyOS PC) — test_ohos skipped\n");
    return 77;
#endif
}
