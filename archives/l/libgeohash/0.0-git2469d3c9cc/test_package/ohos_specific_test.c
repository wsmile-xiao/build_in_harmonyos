/*
 * ohos_specific_test.c — libgeohash HarmonyOS(PC)/OHOS 平台专项测试
 *
 * 与上游 geohash_test.c（固定期望值断言）和 test_package/test.c（消费者 API 验证）
 * 不同，本用例聚焦 OHOS 平台端到端行为：
 *   1. encode→decode 往返一致性（任意精度的坐标恢复误差界）
 *   2. 坐标边界（lat=±90, lng=±180）与非法精度回退（precision<1 或 >12 → 6）
 *   3. 高精度(12)邻居计算的 8 方向完整性（覆盖上游 get_neighbor 堆溢出修复路径，
 *      验证修复在 OHOS 工具链/clang 15 + musl 下成立）
 *   4. dimensions 对 1..20 精度单调性（宽度/高度随精度严格递减）
 *
 * 在 OHOS aarch64 目标（os=OHOS, clang 15, libc++/musl）下编译运行。
 * 任何断言失败返回非 0 退出码。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "geohash.h"

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("OHOS-FAIL: %s\n", msg); failures++; } \
    else { printf("OHOS-PASS: %s\n", msg); } \
} while (0)

static int approx(double a, double b, double eps) {
    double diff = a - b;
    if (diff < 0) diff = -diff;
    return diff <= eps;
}

int main(void) {
    /* 1. encode→decode 往返一致性 */
    const char *cases[][2] = {
        {"wtw3sjq6", "51.501000, -0.142000"},   /* London */
        {"u4pruydqqvj", "52.205000, 0.119000"},  /* Cambridge */
        {"9q8yyk8h", "37.774000, -122.419000"},  /* SF */
        {"xn77hzzv", "35.689000, 139.692000"},   /* Tokyo */
    };
    for (int i = 0; i < 4; i++) {
        GeoCoord c = geohash_decode((char *)cases[i][0]);
        int len = (int)strlen(cases[i][0]);
        char *h = geohash_encode(c.latitude, c.longitude, len);
        CHECK(h != NULL && strcmp(h, cases[i][0]) == 0,
              "roundtrip encode(decode(h)) == h");
        /* 解码中心应在边界框内 */
        CHECK(c.south <= c.latitude && c.latitude <= c.north &&
              c.west <= c.longitude && c.longitude <= c.east,
              "decode center within bounding box");
        free(h);
    }

    /* 2. 坐标边界与非法精度回退 */
    char *h = geohash_encode(90.0, 180.0, 12);
    CHECK(h != NULL && strlen(h) == 12, "encode(lat=90,lng=180,12) len 12");
    free(h);
    h = geohash_encode(-90.0, -180.0, 12);
    CHECK(h != NULL && strlen(h) == 12, "encode(lat=-90,lng=-180,12) len 12");
    free(h);
    h = geohash_encode(40.018141, -105.274858, 0);   /* precision 0 → 默认 6 */
    CHECK(h != NULL && strcmp(h, "9xj5sm") == 0, "precision=0 falls back to 6");
    free(h);
    h = geohash_encode(40.018141, -105.274858, 21);  /* precision 21 → 默认 6 */
    CHECK(h != NULL && strcmp(h, "9xj5sm") == 0, "precision=21 falls back to 6");
    free(h);

    /* 3. 高精度(12)邻居 8 方向完整性（get_neighbor 堆溢出修复验证） */
    char **n = geohash_neighbors("9xj5smj4w40m");
    const char *expected[8] = {"9xj5smj4w40q", "9xj5smj4w40w", "9xj5smj4w40t",
                               "9xj5smj4w40s", "9xj5smj4w40k", "9xj5smj4w40h",
                               "9xj5smj4w40j", "9xj5smj4w40n"};
    int ok = (n != NULL);
    for (int i = 0; ok && i < 8; i++)
        ok = (n[i] != NULL && strlen(n[i]) == 12 && strcmp(n[i], expected[i]) == 0);
    CHECK(ok, "high-precision(12) neighbors all 8 correct & full length");
    if (n) { for (int i = 0; i < 8; i++) free(n[i]); free(n); }

    /* 4. dimensions 单调性（精度 1..20 严格递减） */
    int mono = 1;
    double prev_w = 360.0, prev_h = 180.0;
    for (int p = 1; p <= 20; p++) {
        GeoBoxDimension d = geohash_dimensions_for_precision(p);
        if (!(d.width < prev_w && d.height < prev_h)) { mono = 0; break; }
        prev_w = d.width; prev_h = d.height;
    }
    CHECK(mono, "dimensions strictly decreasing for precision 1..20");
    GeoBoxDimension d1 = geohash_dimensions_for_precision(1);
    CHECK(approx(d1.width, 45.0, 1e-9) && approx(d1.height, 45.0, 1e-9),
          "dimensions_for_precision(1) == 45x45");

    printf("ohos_specific_test: %d failure(s)\n", failures);
    return failures ? 1 : 0;
}
