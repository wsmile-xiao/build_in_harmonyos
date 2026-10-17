/*
 * test_lodepng.cpp — lodepng 消费者测试（链接 Conan 包内 liblodepng）。
 *
 * 实质调用被测包公开 API（R34），共 5 组断言：
 *   1. LODEPNG_VERSION_STRING 为上游快照版本 "20241228"（证明链的是本包）
 *   2. lodepng::encode 产出带标准 PNG 签名的字节流
 *   3. lodepng::decode 还原宽高且像素与原图逐字节一致（编码往返）
 *   4. lodepng_error_text(0) 返回非空可读信息
 *   5. 截断的 PNG 解码返回非零错误（反向对照：harness 能抓到失败）
 *
 * 全部通过才打印 HMBS_TEST_PACKAGE_RESULT（discovered=5）。
 */
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "lodepng.h"

static int g_failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (cond) {                                        \
            printf("  [PASS] %s\n", msg);                  \
        } else {                                           \
            printf("  [FAIL] %s\n", msg);                  \
            g_failures++;                                  \
        }                                                  \
    } while (0)

int main() {
    printf("lodepng test_package: encode/decode roundtrip\n");

    /* Group 1: version identity of the pinned snapshot. */
    {
        const char* ver = LODEPNG_VERSION_STRING;
        printf("  LODEPNG_VERSION_STRING = %s\n", ver ? ver : "(null)");
        CHECK(ver && std::string(ver) == "20241228", "version string is 20241228");
    }

    /* Build a 16x16 RGBA gradient (compressible, non-trivial). */
    const unsigned W = 16;
    const unsigned H = 16;
    std::vector<unsigned char> image(W * H * 4);
    for (unsigned y = 0; y < H; y++) {
        for (unsigned x = 0; x < W; x++) {
            image[4 * W * y + 4 * x + 0] = (unsigned char)(x * 16);
            image[4 * W * y + 4 * x + 1] = (unsigned char)(y * 16);
            image[4 * W * y + 4 * x + 2] = (unsigned char)128;
            image[4 * W * y + 4 * x + 3] = 255;
        }
    }

    /* Group 2: encode produces a valid PNG signature. */
    std::vector<unsigned char> png;
    unsigned error = lodepng::encode(png, image, W, H);
    CHECK(error == 0, "lodepng::encode returns 0");
    static const unsigned char kSig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    CHECK(png.size() > 8 && memcmp(&png[0], kSig, 8) == 0, "encoded bytes carry PNG signature");
    printf("  encoded %u bytes\n", (unsigned)png.size());

    /* Group 3: decode recovers dimensions and exact pixels. */
    {
        std::vector<unsigned char> decoded;
        unsigned w = 0;
        unsigned h = 0;
        unsigned dec_err = lodepng::decode(decoded, w, h, png);
        CHECK(dec_err == 0, "lodepng::decode returns 0");
        CHECK(w == W && h == H, "decoded dimensions are 16x16");
        CHECK(decoded.size() == image.size() && memcmp(&decoded[0], &image[0], image.size()) == 0,
              "decoded pixels match original exactly");
    }

    /* Group 4: error text API is usable. */
    {
        const char* text = lodepng_error_text(0);
        printf("  lodepng_error_text(0) = %s\n", text ? text : "(null)");
        CHECK(text && text[0] != '\0', "lodepng_error_text(0) is non-empty");
    }

    /* Group 5: negative control — truncated PNG must fail to decode. */
    {
        std::vector<unsigned char> broken(png.begin(), png.begin() + png.size() / 2);
        std::vector<unsigned char> decoded;
        unsigned w = 0;
        unsigned h = 0;
        unsigned dec_err = lodepng::decode(decoded, w, h, broken);
        CHECK(dec_err != 0, "truncated PNG decode returns non-zero error");
    }

    if (g_failures == 0) {
        printf("lodepng consumer assertions: 5 groups passed\n");
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
               "\"command\":\"./test_lodepng\",\"discovered\":5,\"passedCount\":5}\n");
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,"
           "\"command\":\"./test_lodepng\",\"discovered\":5,\"passedCount\":%d}\n",
           5 - g_failures);
    return 1;
}
