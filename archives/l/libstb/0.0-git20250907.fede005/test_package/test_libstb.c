/* test_libstb.c — 消费者测试：实质调用 libstb（stb 全集）中 6 个头文件的 API
 *
 * 覆盖：
 *   1. stb_image_write + stb_image：8x8 RGB 渐变 → PNG（内存编码）→ 无损解码，逐字节比对
 *   2. stb_ds：动态数组 arrput/arrlen + int key 哈希表 hmput/hmget + 字符串哈希表 shput/shget
 *      （仅使用 stb_ds/0.67 真机包已验证过的安全 API 集，避开上游自认
 *       "currently broken for clang" 的 C 模式 literal-array key 路径）
 *   3. stb_sprintf：整数/字符串/宽度与浮点格式化，与标准结果比对
 *   4. stb_rect_pack：4 个 20x10 矩形装入 64x64，断言全部装入、不出界、两两不重叠
 *   5. stb_divide：stb_div_trunc/floor/eucl(-7,2) 与数学定义比对
 *
 * 多个 STB_*_IMPLEMENTATION 实现段放在同一翻译单元，是 stb 官方支持的用法。
 * 不用 assert()：Release/NDEBUG 下 assert 会被编译掉导致空壳测试；
 * 全部为显式判定 + 计数，main 按失败数返回非 0。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#define STB_DS_IMPLEMENTATION
#include "stb_ds.h"
#define STB_SPRINTF_IMPLEMENTATION
#include "stb_sprintf.h"
#define STB_RECT_PACK_IMPLEMENTATION
#include "stb_rect_pack.h"
#define STB_DIVIDE_IMPLEMENTATION
#include "stb_divide.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        checks++;                                          \
        if (cond) {                                        \
            printf("PASS %s\n", msg);                      \
        } else {                                           \
            fprintf(stderr, "FAIL %s\n", msg);             \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_image_roundtrip(void)
{
    enum { W = 8, H = 8, C = 3 };
    unsigned char pixels[W * H * C];
    unsigned char *png, *dec;
    int len = 0, w = 0, h = 0, n = 0;
    int i;

    for (i = 0; i < W * H * C; i++)
        pixels[i] = (unsigned char)(i * 7);

    png = stbi_write_png_to_mem(pixels, W * C, W, H, C, &len);
    CHECK(png != NULL && len > 0, "stb_image_write: stbi_write_png_to_mem");
    if (!png)
        return;

    dec = stbi_load_from_memory(png, len, &w, &h, &n, 0);
    CHECK(dec != NULL, "stb_image: stbi_load_from_memory(PNG)");
    if (dec) {
        CHECK(w == W && h == H && n == C, "stb_image: 解码尺寸/通道往返一致");
        CHECK(memcmp(pixels, dec, (size_t)(W * H * C)) == 0,
              "stb_image: PNG 无损像素往返（memcmp 逐字节）");
        stbi_image_free(dec);
    }
    free(png);
}

static void test_ds(void)
{
    int *arr = NULL;
    struct { int key, value; } *map = NULL;
    struct { char *key; int value; } *smap = NULL;

    arrput(arr, 1);
    arrput(arr, 2);
    arrput(arr, 3);
    CHECK(arrlen(arr) == 3 && arr[0] == 1 && arr[2] == 3,
          "stb_ds: arrput/arrlen/下标访问");
    arrfree(arr);

    hmput(map, 42, 7);
    hmput(map, 100, 200);
    CHECK(hmlen(map) == 2 && hmget(map, 42) == 7 && hmget(map, 100) == 200,
          "stb_ds: hmput/hmget/hmlen（int key 哈希表）");
    hmfree(map);

    shput(smap, "alpha", 1);
    shput(smap, "beta", 2);
    CHECK(shlen(smap) == 2 && shget(smap, "alpha") == 1 && shget(smap, "beta") == 2,
          "stb_ds: shput/shget/shlen（字符串 key 哈希表）");
    shfree(smap);
}

static void test_sprintf(void)
{
    char buf[128];

    stbsp_sprintf(buf, "%d-%s-%05d", 42, "stb", 7);
    CHECK(strcmp(buf, "42-stb-00007") == 0, "stb_sprintf: 整数/字符串/宽度格式化");

    stbsp_sprintf(buf, "%.2f", 3.14159);
    CHECK(strcmp(buf, "3.14") == 0, "stb_sprintf: 浮点格式化");

    stbsp_sprintf(buf, "%x/%X", 255, 255);
    CHECK(strcmp(buf, "ff/FF") == 0, "stb_sprintf: 十六进制格式化");
}

static void test_rect_pack(void)
{
    stbrp_context ctx;
    stbrp_node nodes[64];
    stbrp_rect rects[4];
    int i, j, packed = 1, in_bounds = 1, no_overlap = 1;

    for (i = 0; i < 4; i++) {
        rects[i].id = i;
        rects[i].x = 0;
        rects[i].y = 0;
        rects[i].w = 20;
        rects[i].h = 10;
        rects[i].was_packed = 0;
    }

    stbrp_init_target(&ctx, 64, 64, nodes, 64);
    stbrp_pack_rects(&ctx, rects, 4);

    for (i = 0; i < 4; i++) {
        packed &= rects[i].was_packed;
        in_bounds &= (rects[i].x + rects[i].w <= 64 && rects[i].y + rects[i].h <= 64);
        for (j = i + 1; j < 4; j++) {
            int disjoint =
                rects[i].x + rects[i].w <= rects[j].x || rects[j].x + rects[j].w <= rects[i].x ||
                rects[i].y + rects[i].h <= rects[j].y || rects[j].y + rects[j].h <= rects[i].y;
            no_overlap &= disjoint;
        }
    }
    CHECK(packed, "stb_rect_pack: 4 个 20x10 矩形全部装入 64x64");
    CHECK(in_bounds, "stb_rect_pack: 所有矩形在目标边界内");
    CHECK(no_overlap, "stb_rect_pack: 矩形两两不重叠");
}

static void test_divide(void)
{
    CHECK(stb_div_trunc(-7, 2) == -3, "stb_divide: stb_div_trunc(-7,2) == -3（向零取整）");
    CHECK(stb_div_floor(-7, 2) == -4, "stb_divide: stb_div_floor(-7,2) == -4（向下取整）");
    CHECK(stb_div_eucl(-7, 2) == -4, "stb_divide: stb_div_eucl(-7,2) == -4（欧几里得）");
}

int main(void)
{
    printf("Testing libstb 0.0-git20250907.fede005 (nothings/stb @ fede005)...\n");

    test_image_roundtrip();
    test_ds();
    test_sprintf();
    test_rect_pack();
    test_divide();

    printf("\nTotal checks: %d, failed: %d\n", checks, failures);
    if (failures == 0) {
        printf("All tests passed!\n");
        return 0;
    }
    fprintf(stderr, "%d test(s) FAILED\n", failures);
    return 1;
}
