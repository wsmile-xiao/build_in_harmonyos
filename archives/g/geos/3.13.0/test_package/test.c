/*
 * GEOS 3.13.0 test_package - 实质调用 GEOS C API
 * R34: 测试必须实质依赖被测包的 API，禁止空壳打印测试
 */
#include <geos_c.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static void geos_notice_handler(const char *msg, void *userdata) {
    (void)msg;
    (void)userdata;
}

static void geos_error_handler(const char *msg, void *userdata) {
    (void)msg;
    (void)userdata;
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    /* 初始化 GEOS context（thread-safe API） */
    GEOSContextHandle_t ctx = GEOS_init_r();
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: GEOS_init_r() returned NULL\n");
        return 1;
    }
    GEOSContext_setNoticeMessageHandler_r(ctx, geos_notice_handler, NULL);
    GEOSContext_setErrorMessageHandler_r(ctx, geos_error_handler, NULL);

    /* 查询 GEOS 版本 */
    const char *version = GEOSversion();
    if (version == NULL) {
        fprintf(stderr, "FAIL: GEOSversion() returned NULL\n");
        GEOS_finish_r(ctx);
        return 1;
    }
    printf("GEOS version: %s\n", version);

    /* 创建两个 POINT 几何对象 */
    GEOSGeometry *p1 = GEOSGeom_createPointFromXY_r(ctx, 0.0, 0.0);
    GEOSGeometry *p2 = GEOSGeom_createPointFromXY_r(ctx, 1.0, 1.0);
    if (p1 == NULL || p2 == NULL) {
        fprintf(stderr, "FAIL: GEOSGeom_createPointFromXY_r() returned NULL\n");
        if (p1) GEOSGeom_destroy_r(ctx, p1);
        if (p2) GEOSGeom_destroy_r(ctx, p2);
        GEOS_finish_r(ctx);
        return 1;
    }

    /* 计算两点距离（实质调用 GEOS 几何运算 API） */
    double dist = -1.0;
    int rc = GEOSDistance_r(ctx, p1, p2, &dist);
    if (rc == 0) {
        fprintf(stderr, "FAIL: GEOSDistance_r() failed\n");
        GEOSGeom_destroy_r(ctx, p1);
        GEOSGeom_destroy_r(ctx, p2);
        GEOS_finish_r(ctx);
        return 1;
    }
    printf("Distance between POINT(0 0) and POINT(1 1): %f\n", dist);

    /* 验证距离 = sqrt(2) ≈ 1.414214 */
    const double expected = 1.4142135623730951;
    if (fabs(dist - expected) > 1e-6) {
        fprintf(stderr, "FAIL: distance %f != expected %f\n", dist, expected);
        GEOSGeom_destroy_r(ctx, p1);
        GEOSGeom_destroy_r(ctx, p2);
        GEOS_finish_r(ctx);
        return 1;
    }

    /* 测试 WKT 读取 */
    GEOSWKTReader *reader = GEOSWKTReader_create_r(ctx);
    if (reader == NULL) {
        fprintf(stderr, "FAIL: GEOSWKTReader_create_r() returned NULL\n");
        GEOSGeom_destroy_r(ctx, p1);
        GEOSGeom_destroy_r(ctx, p2);
        GEOS_finish_r(ctx);
        return 1;
    }
    GEOSGeometry *g = GEOSWKTReader_read_r(ctx, reader, "LINESTRING (0 0, 10 10)");
    if (g == NULL) {
        fprintf(stderr, "FAIL: GEOSWKTReader_read_r() returned NULL\n");
        GEOSWKTReader_destroy_r(ctx, reader);
        GEOSGeom_destroy_r(ctx, p1);
        GEOSGeom_destroy_r(ctx, p2);
        GEOS_finish_r(ctx);
        return 1;
    }
    printf("Read LINESTRING from WKT, type=%d\n", (int)GEOSGeomTypeId_r(ctx, g));

    /* 清理 */
    GEOSGeom_destroy_r(ctx, g);
    GEOSWKTReader_destroy_r(ctx, reader);
    GEOSGeom_destroy_r(ctx, p1);
    GEOSGeom_destroy_r(ctx, p2);
    GEOS_finish_r(ctx);

    printf("PASS: GEOS C API distance calculation and WKT parsing\n");
    return 0;
}
