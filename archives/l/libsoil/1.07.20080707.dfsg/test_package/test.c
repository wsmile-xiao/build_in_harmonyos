/*
 * test_package for libsoil 1.07.20080707.dfsg
 *
 * 实质调用被测库 API（R34，禁空壳）：
 *   - SOIL_load_image：解码包内测试图片 img_test.bmp/png/tga/dds（4 种格式），
 *     校验尺寸(256x256)、通道数、左上角关键像素 (0,0,255)；
 *   - SOIL_load_image(force_channels=SOIL_LOAD_RGB)：通道转换路径；
 *   - SOIL_save_image：把解码出的 RGBA 图像另存为 BMP，再重新解码校验往返一致性；
 *   - SOIL_free_image_data / SOIL_last_result。
 *
 * 测试图片不随仓库提交（二进制文件会导致 CI checkout-pr 的 git apply
 * 失败，见 make_images.py 头注释），由 test_package/CMakeLists.txt 在
 * 配置/构建期用 make_images.py 确定性生成到 ${IMAGES_DIR}（argv[1]）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "SOIL.h"

static int failures = 0;
static int total = 0;

static void expect(int cond, const char *msg) {
    total++;
    if (!cond) {
        failures++;
        printf("  [FAIL] %s\n", msg);
    } else {
        printf("  [PASS] %s\n", msg);
    }
}

/* 解码单个图片文件并校验尺寸/通道数/关键像素 */
static void decode_and_check(const char *path, int exp_w, int exp_h,
                             int exp_ch, int force,
                             int exp_r, int exp_g, int exp_b) {
    int w = 0, h = 0, ch = 0;
    unsigned char *img = SOIL_load_image(path, &w, &h, &ch, force);
    if (!img) {
        printf("  [FAIL] %s: SOIL_load_image 返回 NULL: %s\n",
               path, SOIL_last_result());
        total++;
        failures++;
        return;
    }
    char msg[256];
    snprintf(msg, sizeof msg, "%s: 解码成功", path);
    expect(1, msg);
    snprintf(msg, sizeof msg, "%s: 尺寸 %dx%d (期望 %dx%d)", path, w, h, exp_w, exp_h);
    expect(w == exp_w && h == exp_h, msg);
    snprintf(msg, sizeof msg, "%s: 通道数 %d (期望 %d)", path, ch, exp_ch);
    expect(ch == exp_ch, msg);
    /* 左上角像素（BMP/PNG/TGA/DDS 均为同一蓝色测试图） */
    {
        int r = img[0];
        int g = img[ch > 1 ? 1 : 0];
        int b = img[ch > 2 ? 2 : 0];
        snprintf(msg, sizeof msg, "%s: 左上角像素 RGB(%d,%d,%d) 期望 (%d,%d,%d)",
                 path, r, g, b, exp_r, exp_g, exp_b);
        expect(r == exp_r && g == exp_g && b == exp_b, msg);
    }
    SOIL_free_image_data(img);
}

int main(int argc, char **argv) {
    const char *dir = (argc > 1) ? argv[1] : ".";
    char p[1024];

    printf("== libsoil test_package: 图像解码/编码功能测试 ==\n");

    /* 1. 四种格式解码（R51 补全测试，真实调用被测库 API） */
    snprintf(p, sizeof p, "%s/img_test.bmp", dir);
    decode_and_check(p, 256, 256, 3, SOIL_LOAD_AUTO, 0, 0, 255);
    snprintf(p, sizeof p, "%s/img_test.png", dir);
    decode_and_check(p, 256, 256, 4, SOIL_LOAD_AUTO, 0, 0, 255);
    snprintf(p, sizeof p, "%s/img_test.tga", dir);
    decode_and_check(p, 256, 256, 4, SOIL_LOAD_AUTO, 0, 0, 255);
    snprintf(p, sizeof p, "%s/img_test.dds", dir);
    decode_and_check(p, 256, 256, 4, SOIL_LOAD_AUTO, 0, 0, 255);

    /* 2. force_channels=SOIL_LOAD_RGB：通道转换路径（*channels 仍返回原始通道数） */
    snprintf(p, sizeof p, "%s/img_test.png", dir);
    {
        int w = 0, h = 0, ch = 0;
        unsigned char *img = SOIL_load_image(p, &w, &h, &ch, SOIL_LOAD_RGB);
        char msg[256];
        if (!img) {
            snprintf(msg, sizeof msg, "SOIL_LOAD_RGB: 解码失败: %s", SOIL_last_result());
            expect(0, msg);
        } else {
            snprintf(msg, sizeof msg, "SOIL_LOAD_RGB: 原始通道数 %d (期望 4)", ch);
            expect(ch == 4, msg);
            expect(w == 256 && h == 256, "SOIL_LOAD_RGB: 尺寸 256x256");
            SOIL_free_image_data(img);
        }
    }

    /* 3. SOIL_save_image 往返：RGBA → BMP → 重新解码 */
    snprintf(p, sizeof p, "%s/img_test.png", dir);
    {
        int w = 0, h = 0, ch = 0;
        unsigned char *img = SOIL_load_image(p, &w, &h, &ch, SOIL_LOAD_AUTO);
        char msg[256];
        if (!img) {
            snprintf(msg, sizeof msg, "save 往返: 载入失败: %s", SOIL_last_result());
            expect(0, msg);
        } else {
            const char *out = "soil_roundtrip.bmp";
            int saved = SOIL_save_image(out, SOIL_SAVE_TYPE_BMP, w, h, ch, img);
            snprintf(msg, sizeof msg, "SOIL_save_image BMP 返回 %d (期望 1)", saved);
            expect(saved == 1, msg);
            SOIL_free_image_data(img);
            if (saved) {
                int w2 = 0, h2 = 0, ch2 = 0;
                unsigned char *img2 = SOIL_load_image(out, &w2, &h2, &ch2, SOIL_LOAD_AUTO);
                snprintf(msg, sizeof msg, "往返重载: %dx%dx%d (期望 256x256x3)", w2, h2, ch2);
                expect(img2 != NULL && w2 == w && h2 == h && ch2 == 3, msg);
                SOIL_free_image_data(img2);
            }
        }
    }

    /* 4. SOIL_last_result 非空（错误报告 API 可用） */
    {
        const char *r = SOIL_last_result();
        expect(r != NULL, "SOIL_last_result 返回非空字符串");
    }

    printf("\n结果: %d/%d 项检查通过\n", total - failures, total);
    return failures == 0 ? 0 : 1;
}
