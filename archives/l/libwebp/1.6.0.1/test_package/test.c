/* libwebp 1.6.0.1 功能探针（相对 1.6.0 空壳 dlopen 探针的升级）
 *
 * - 直接链接 libwebp（消费方真实形态，验证 cpp_info.libs 可用）
 * - 核心路径：编解码器运行期版本断言、近无损（VP8 q=100，RGB/alpha≤8）、
 *   有损（q=75，RGB≤64/alpha≤32）RGBA roundtrip、无损（VP8L 专属 API，逐字节）、
 *   容器解析正反例（WebPGetInfo/WebPGetFeatures 拒绝损坏数据、接受有效流）
 * ——全部依赖内建编解码器，任何构建下都应全绿（R34 反空壳）
 *
 * 测试图案设计要点（Windows 本机 PIL 复现实测后修订）：
 * - 无损图案的 alpha 必须避开 0：VP8L 编码器对 alpha=0 像素做 alpha cleanup，
 *   把透明像素 RGB 改写成左邻预测值以利压缩（WebPConfig.exact=0 默认），
 *   透明像素的 RGB 本就不承诺保真；此处 alpha 取 128..255 段
 * - VP8 q=100 仍是有损编码（高频棋盘实测 RGB 偏差可达 100+），
 *   近无损断言只对平滑渐变成立（实测偏差 ≤2，阈值 8 留 4 倍余量）
 */
#include <webp/decode.h>
#include <webp/encode.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_assert = 0;
static int g_fail = 0;

#define CHECK(cond, msg) do { \
    int _n = ++g_assert; \
    if (cond) { printf("PASS [%02d] %s\n", _n, msg); } \
    else { g_fail++; printf("FAIL [%02d] %s\n", _n, msg); } \
} while (0)

/* 无损用高频棋盘（任何差异都逃不掉）；有损用平滑渐变（码率友好，容差判定） */
static unsigned char px_hf(unsigned x, unsigned y, int ch) {
    if (ch == 3) return (unsigned char)(((x * 7 + y * 13) & 0x7f) | 0x80); /* alpha 128..255 */
    return (unsigned char)((x * 7 + y * 13 + ch * 31) & 0xff);
}
static unsigned char px_smooth(unsigned x, unsigned y, int ch) {
    return (unsigned char)(((x + y) * 2 + ch * 8) & 0xff);
}

/* 返回 0=ok / -1=编码失败 / -2=解码失败或尺寸不符 / -3=RGB 超容差 / -4=alpha 超容差 */
static int lossy_roundtrip(int w, int h, float q, int rgb_thr, int alpha_thr,
                           int *rgb_maxd, int *alpha_maxd) {
    uint8_t *rgba = (uint8_t *)malloc((size_t)w * h * 4);
    uint8_t *webp = NULL, *out = NULL;
    int ow = 0, oh = 0, rc = 0;
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++)
            for (int c = 0; c < 4; c++)
                rgba[(y * w + x) * 4 + c] = px_smooth((unsigned)x, (unsigned)y, c);
    size_t sz = WebPEncodeRGBA(rgba, w, h, w * 4, q, &webp);
    if (sz == 0) { rc = -1; goto done; }
    out = WebPDecodeRGBA(webp, sz, &ow, &oh);
    if (out == NULL || ow != w || oh != h) { rc = -2; goto done; }
    for (size_t i = 0; i < (size_t)w * h * 4; i++) {
        int d = rgba[i] - out[i];
        if (d < 0) d = -d;
        if (i % 4 == 3) { if (d > *alpha_maxd) *alpha_maxd = d; }
        else { if (d > *rgb_maxd) *rgb_maxd = d; }
    }
    if (*rgb_maxd > rgb_thr) rc = -3;
    else if (*alpha_maxd > alpha_thr) rc = -4;
done:
    WebPFree(webp); WebPFree(out); free(rgba);
    return rc;
}

int main(void) {
    /* 运行期版本断言：WebPGet{Decoder,Encoder}Version 返回「三字节打包发行版号」
     * (MAJOR<<16)|(MINOR<<8)|REV（vp8_dec.c 实现，decode.h 注释：v2.5.7 is 0x020507），
     * 与 ABI 版本（WEBP_DECODER_ABI_VERSION=0x0210）是两套数。1.6.0 → 0x010600。 */
    int dec_ver = WebPGetDecoderVersion();
    int enc_ver = WebPGetEncoderVersion();
    printf("[dbg] dec_ver=0x%08x enc_ver=0x%08x\n", dec_ver, enc_ver);
    CHECK(dec_ver >= 0x010600, "WebPGetDecoderVersion >= 0x010600 (release packing, 1.6.0)");
    CHECK(enc_ver >= 0x010600, "WebPGetEncoderVersion >= 0x010600 (release packing, 1.6.0)");

    /* 近无损 RGBA roundtrip（q=100，平滑图案容差：RGB/alpha≤8） */
    int rgb_maxd = 0, alpha_maxd = 0;
    CHECK(lossy_roundtrip(16, 16, 100.0f, 8, 8, &rgb_maxd, &alpha_maxd) == 0,
          "near-lossless VP8 RGBA 16x16 roundtrip (q=100, RGB/alpha<=8)");

    /* 有损 RGBA roundtrip（q=75，容差：RGB≤64 / alpha≤32） */
    rgb_maxd = 0; alpha_maxd = 0;
    CHECK(lossy_roundtrip(32, 32, 75.0f, 64, 32, &rgb_maxd, &alpha_maxd) == 0,
          "lossy RGBA 32x32 roundtrip (q=75, RGB<=64/alpha<=32)");

    /* 错误路径：损坏数据被拒绝 */
    static const uint8_t bad[] = "RIFF\x00\x00\x00\x00WEBPVP8 garbage-payload";
    int w = 0, h = 0;
    CHECK(WebPGetInfo(bad, sizeof(bad) - 1, &w, &h) == 0, "WebPGetInfo rejects corrupt payload");

    /* VP8L 专属 API：WebPEncodeLosslessRGBA + WebPDecodeRGB（无 alpha 路径，逐字节） */
    {
        uint8_t rgba16[16 * 16 * 4];
        for (unsigned y = 0; y < 16; y++)
            for (unsigned x = 0; x < 16; x++)
                for (int c = 0; c < 4; c++)
                    rgba16[(y * 16 + x) * 4 + c] = px_hf(x, y, c);
        uint8_t *webp = NULL;
        size_t sz = WebPEncodeLosslessRGBA(rgba16, 16, 16, 16 * 4, &webp);
        CHECK(sz > 0, "WebPEncodeLosslessRGBA 16x16 (VP8L)");
        int ow = 0, oh = 0;
        uint8_t *rgb = WebPDecodeRGB(webp, sz, &ow, &oh);
        CHECK(rgb != NULL && ow == 16 && oh == 16, "WebPDecodeRGB dims (VP8L)");
        int rgb_ok = 1;
        if (rgb) {
            for (unsigned y = 0; y < 16 && rgb_ok; y++)
                for (unsigned x = 0; x < 16 && rgb_ok; x++)
                    for (int c = 0; c < 3; c++)
                        if (rgb[(y * 16 + x) * 3 + c] != px_hf(x, y, c)) {
                            printf("[dbg] vp8l first mismatch x=%u y=%u ch=%d expect=%u got=%u\n",
                                   x, y, c, px_hf(x, y, c), rgb[(y * 16 + x) * 3 + c]);
                            rgb_ok = 0;
                        }
        }
        CHECK(rgb_ok, "WebPDecodeRGB pixel-exact (VP8L)");
        WebPBitstreamFeatures feat;
        CHECK(WebPGetFeatures(webp, sz, &feat) == VP8_STATUS_OK && feat.width == 16 && feat.height == 16,
              "WebPGetFeatures parses container (16x16)");
        CHECK(WebPGetFeatures(bad, sizeof(bad) - 1, &feat) != VP8_STATUS_OK,
              "WebPGetFeatures rejects corrupt payload");
        WebPFree(webp); WebPFree(rgb);
    }

    /* 有效流正例（4x4 小图） */
    {
        uint8_t small[4 * 4 * 4];
        for (int i = 0; i < 4 * 4 * 4; i++) small[i] = (uint8_t)i;
        uint8_t *webp = NULL;
        size_t sz = WebPEncodeRGBA(small, 4, 4, 16, 90.0f, &webp);
        CHECK(sz > 0 && WebPGetInfo(webp, sz, &w, &h) && w == 4 && h == 4,
              "WebPGetInfo accepts valid stream (4x4)");
        WebPFree(webp);
    }

    printf("\nlibwebp probe: %d/%d assertions passed%s\n",
           g_assert - g_fail, g_assert, g_fail ? " — FAILED" : " — ALL GREEN");
    return g_fail ? 1 : 0;
}
