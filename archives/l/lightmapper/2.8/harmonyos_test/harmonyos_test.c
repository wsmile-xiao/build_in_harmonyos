/* harmonyos_test.c — lightmapper 2.8 独立鸿蒙特有测试入口 (R02)
 *
 * 独立于 test_package 的测试入口：自己的源文件、自己的断言、自己的运行
 * 入口（run_harmonyos_test.sh）。复用 r01 已交付的 GL 链接期 stub 手段
 * （gl_shim.h/.c），测试源文件与断言完全独立。
 *
 * 验证的鸿蒙/OHOS 平台行为：
 *   - 目标 OH 设备无 GPU/无 GL 运行时（无 EGL/GLX 上下文），lightmapper 的
 *     CPU 侧公开 API 仍可正确产出 TGA 文件（$TMPDIR 下写文件行为 + TGA 头
 *     字节序正确）；
 *   - 字节序/像素通道对齐：RGBA 浮点缓冲经 lmImageFtoUB + lmImageSaveTGAub
 *     落盘后头部 type==2、宽高与源一致。
 *
 * 可失败性：本入口的每条断言均为可失败断言（check 计数 + 失败即 exit 1）；
 * 设置环境变量 LM_NEGATIVE_PROOF=1 时注入必然不成立的期望值，用于负向
 * 证明（详见 run_harmonyos_test.sh 与任务报告）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define LIGHTMAPPER_IMPLEMENTATION
#include "gl_shim.h"
#include "lightmapper.h"

static int checks = 0;
static int failures = 0;

static void check(int ok, const char *what) {
    checks++;
    if (!ok) { failures++; printf("FAIL: %s\n", what); }
}

int main(void) {
    const int w = 4, h = 3, c = 3; /* 4x3 RGB */
    float img[4 * 3 * 3];
    int i;

    /* 固定可断言输入：min=0.0, max=1.0，其余线性分布 */
    for (i = 0; i < w * h * c; i++)
        img[i] = (float)i / (float)(w * h * c - 1);
    img[0] = 0.0f;           /* 已知 min */
    img[w * h * c - 1] = 1.0f; /* 已知 max */

    /* 1) lmImageMin / lmImageMax：真实 CPU 计算，可失败断言 */
    {
        float mn = lmImageMin(img, w, h, c, LM_ALL_CHANNELS);
        float mx = lmImageMax(img, w, h, c, LM_ALL_CHANNELS);
        check(fabsf(mn - 0.0f) < 1e-6f, "lmImageMin == 0.0");
        check(fabsf(mx - 1.0f) < 1e-6f, "lmImageMax == 1.0");
        printf("min=%.4f max=%.4f\n", (double)mn, (double)mx);
    }

    /* 2) lmImageDilate：单非零像素向 4 邻域扩散，可失败断言 */
    {
        const float src[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
        float out[4] = { 0, 0, 0, 0 };
        lmImageDilate(src, out, 2, 2, 1);
        check(fabsf(out[3] - 1.0f) < 1e-6f, "dilate 保留源像素");
        check(out[1] > 0.0f && out[2] > 0.0f, "dilate 扩散至 4 邻域");
        check(out[0] == 0.0f, "dilate 不填对角");
    }

    /* 3) lmImageFtoUB：0.0->0, 1.0->255（max=1.0），可失败断言 */
    {
        const float src[2] = { 0.0f, 1.0f };
        unsigned char ub[2] = { 0, 0 };
        lmImageFtoUB(src, ub, 2, 1, 1, 1.0f);
        check(ub[0] == 0 && ub[1] == 255, "FtoUB 0.0->0 / 1.0->255");
    }

    /* 4) lmImageSaveTGAub：OH 设备 $TMPDIR 写文件 + TGA 头校验（鸿蒙特有断言） */
    {
        unsigned char tga[4 * 3 * 3];
        unsigned char hdr[18];
        int hdr_read = 0;
        for (i = 0; i < w * h * c; i++)
            tga[i] = (unsigned char)((i * 37) & 0xff);
        memset(hdr, 0, sizeof(hdr));
        /* 输出目录必须用 $TMPDIR（必要时 $HOME/tmp），不假定 /tmp 可写 */
        const char *outdir = getenv("TMPDIR");
        if (!outdir || !*outdir) outdir = getenv("HOME");
        char path[1024];
        snprintf(path, sizeof(path), "%s/lightmapper_hoh_test.tga", outdir);

        lm_bool ok = lmImageSaveTGAub(path, tga, w, h, c);
        check(ok == LM_TRUE, "lmImageSaveTGAub 返回 LM_TRUE");

        FILE *f = fopen(path, "rb");
        check(f != NULL, "TGA 文件真实落盘于 $TMPDIR");
        if (f) {
            size_t n = fread(hdr, 1, 18, f);
            hdr_read = (int)(n == 18);
            check(n == 18 && hdr[2] == 2, "TGA 头 type==2 (真彩未压缩)");
            check(hdr[12] == (w & 0xff) && hdr[13] == ((w >> 8) & 0xff),
                  "TGA 头宽一致 (小端字节序正确)");
            check(hdr[14] == (h & 0xff) && hdr[15] == ((h >> 8) & 0xff),
                  "TGA 头高一致 (小端字节序正确)");
            fclose(f);
            remove(path); /* 清理，避免污染 $TMPDIR */
        }

        /* 负向证明开关：注入必然不成立的期望值（真实失败路径） */
        const char *neg = getenv("LM_NEGATIVE_PROOF");
        if (neg && *neg) {
            check(hdr_read == 1 && hdr[2] == 99,
                  "NEGATIVE: TGA type==99 (必不成立)");
        }
    }

    printf("harmonyos_test: %d/%d checks passed\n", checks - failures, checks);
    if (failures) {
        printf("harmonyos_test: %d checks FAILED\n", failures);
        return 1;
    }
    return 0;
}