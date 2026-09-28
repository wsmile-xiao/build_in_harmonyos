/*
 * test_libgeohash.c — Conan test_package 消费者测试（R34/PF3）
 *
 * 通过公开头文件 geohash.h 与静态库 libgeohash.a 验证：
 *   1. geohash_encode：40.018141,-105.274858 精度12 → "9xj5smj4w40m"
 *   2. geohash_decode：ezs42 → 边界框与中心坐标
 *   3. geohash_neighbors：高精度(≥8)邻居计算（覆盖上游堆溢出修复路径）
 *   4. geohash_dimensions_for_precision
 *
 * 任何断言失败返回非 0 退出码。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "geohash.h"

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

static int approx_eq(double a, double b) {
    double diff = a - b;
    if (diff < 0) diff = -diff;
    return diff < 1e-9;
}

int main(void) {
    /* 1. Encode */
    char *h = geohash_encode(40.018141, -105.274858, 12);
    CHECK(h != NULL && strcmp(h, "9xj5smj4w40m") == 0, "encode(40.018141,-105.274858,12) == 9xj5smj4w40m");
    free(h);

    h = geohash_encode(42.60498046875, -5.60302734375, 5);
    CHECK(h != NULL && strcmp(h, "ezs42") == 0, "encode(42.60498,-5.60303,5) == ezs42");
    free(h);

    /* 2. Decode */
    GeoCoord c = geohash_decode("ezs42");
    CHECK(approx_eq(c.latitude, 42.60498046875), "decode(ezs42).latitude");
    CHECK(approx_eq(c.longitude, -5.60302734375), "decode(ezs42).longitude");
    CHECK(approx_eq(c.north, 42.626953125) && approx_eq(c.south, 42.5830078125),
          "decode(ezs42) north/south");
    CHECK(approx_eq(c.east, -5.5810546875) && approx_eq(c.west, -5.625),
          "decode(ezs42) east/west");

    /* 3. Neighbors — 高精度路径（上游 get_neighbor 堆溢出修复验证） */
    char **n = geohash_neighbors("9xj5smj4w40m");
    const char *expected[8] = {"9xj5smj4w40q", "9xj5smj4w40w", "9xj5smj4w40t",
                               "9xj5smj4w40s", "9xj5smj4w40k", "9xj5smj4w40h",
                               "9xj5smj4w40j", "9xj5smj4w40n"};
    int ok = (n != NULL);
    for (int i = 0; ok && i < 8; i++)
        ok = (n[i] != NULL && strcmp(n[i], expected[i]) == 0);
    CHECK(ok, "neighbors(9xj5smj4w40m) all 8 correct (high precision)");
    if (n) {
        for (int i = 0; i < 8; i++) free(n[i]);
        free(n);
    }

    /* 4. Dimensions — precision 2: lat 5 次对折(180/32=5.625), lng 5 次对折(360/32=11.25) */
    GeoBoxDimension d = geohash_dimensions_for_precision(2);
    CHECK(approx_eq(d.width, 11.25) && approx_eq(d.height, 5.625),
          "dimensions_for_precision(2)");

    printf("test_libgeohash: %d failure(s)\n", failures);
    return failures ? 1 : 0;
}
