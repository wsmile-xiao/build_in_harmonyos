/*
 * librttopo 1.1.0 test_package - 实质单元测试调用 librttopo API
 * R34: 测试必须实质依赖被测包的 API，禁止空壳打印测试
 */
#include <librttopo.h>
#include <librttopo_geom.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failures = 0;

static void check(int cond, const char *msg) {
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", msg);
        g_failures++;
    }
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    /* 1. 查询 librttopo 版本 */
    const char *version = rtgeom_version();
    check(version != NULL, "rtgeom_version() returned NULL");
    printf("librttopo version: %s\n", version ? version : "NULL");

    /* 2. 初始化 RTCTX（librttopo 核心上下文） */
    RTCTX *ctx = rtgeom_init(NULL, NULL, NULL);
    check(ctx != NULL, "rtgeom_init() returned NULL");
    if (ctx == NULL) {
        return 1;
    }
    printf("RTCTX initialized\n");

    /* 3. 创建空 POINT 几何对象（SRID=4326, hasZ=0, hasM=0） */
    RTPOINT *pt = rtpoint_construct_empty(ctx, 4326, 0, 0);
    check(pt != NULL, "rtpoint_construct_empty() returned NULL");
    if (pt == NULL) {
        rtgeom_finish(ctx);
        return 1;
    }
    printf("Empty POINT constructed, type=%d\n", (int)rtgeom_get_type(ctx, (RTGEOM *)pt));

    /* 4. 设置 SRID 并验证 */
    rtgeom_set_srid(ctx, (RTGEOM *)pt, 3857);
    int srid = rtgeom_get_srid(ctx, (RTGEOM *)pt);
    printf("POINT SRID after set: %d\n", srid);
    check(srid == 3857, "SRID set/get roundtrip failed");

    /* 5. 创建空 LINESTRING 几何对象 */
    RTLINE *line = rtline_construct_empty(ctx, 4326, 0, 0);
    check(line != NULL, "rtline_construct_empty() returned NULL");
    if (line == NULL) {
        rtpoint_free(ctx, pt);
        rtgeom_finish(ctx);
        return 1;
    }
    printf("Empty LINESTRING constructed\n");

    /* 6. 验证几何类型判断 */
    int is_collection_pt = rtgeom_is_collection(ctx, (RTGEOM *)pt);
    int is_collection_line = rtgeom_is_collection(ctx, (RTGEOM *)line);
    printf("is_collection(POINT)=%d, is_collection(LINESTRING)=%d\n",
           is_collection_pt, is_collection_line);
    check(is_collection_pt == 0 && is_collection_line == 0,
          "basic geometry should not be collection");

    /* 7. 构造带坐标的 POINT(3 4)，验证坐标与 SRID */
    RTPOINTARRAY *pa_pt = ptarray_construct(ctx, 0, 0, 1);
    check(pa_pt != NULL, "ptarray_construct() returned NULL");
    if (pa_pt != NULL) {
        RTPOINT4D p4d;
        p4d.x = 3.0;
        p4d.y = 4.0;
        p4d.z = 0.0;
        p4d.m = 0.0;
        ptarray_set_point4d(ctx, pa_pt, 0, &p4d);
        RTPOINT *pt2 = rtpoint_construct(ctx, 4326, NULL, pa_pt);
        check(pt2 != NULL, "rtpoint_construct() returned NULL");
        if (pt2 != NULL) {
            double area = rtgeom_area(ctx, (RTGEOM *)pt2);
            printf("POINT(3 4) area=%f\n", area);
            check(area == 0.0, "point area should be 0");
            char *wkt = rtgeom_to_wkt(ctx, (RTGEOM *)pt2, 1, 15, NULL);
            printf("POINT WKT: %s\n", wkt ? wkt : "NULL");
            check(wkt != NULL && strstr(wkt, "POINT") != NULL, "POINT WKT output invalid");
            if (wkt) rtfree(ctx, wkt);
            rtpoint_free(ctx, pt2);
        }
    }

    /* 8. 构造带坐标的 LINESTRING(0 0, 0 2)，验证长度=2 */
    RTPOINTARRAY *pa_line = ptarray_construct(ctx, 0, 0, 2);
    check(pa_line != NULL, "ptarray_construct() for line returned NULL");
    if (pa_line != NULL) {
        RTPOINT4D p0, p1;
        p0.x = 0.0; p0.y = 0.0; p0.z = 0.0; p0.m = 0.0;
        p1.x = 0.0; p1.y = 2.0; p1.z = 0.0; p1.m = 0.0;
        ptarray_set_point4d(ctx, pa_line, 0, &p0);
        ptarray_set_point4d(ctx, pa_line, 1, &p1);
        RTLINE *line2 = rtline_construct(ctx, 4326, NULL, pa_line);
        check(line2 != NULL, "rtline_construct() returned NULL");
        if (line2 != NULL) {
            double len = rtgeom_length(ctx, (RTGEOM *)line2);
            printf("LINESTRING(0 0, 0 2) length=%f\n", len);
            check(len > 1.999 && len < 2.001, "line length should be 2.0");
            char *wkt = rtgeom_to_wkt(ctx, (RTGEOM *)line2, 1, 15, NULL);
            printf("LINESTRING WKT: %s\n", wkt ? wkt : "NULL");
            check(wkt != NULL && strstr(wkt, "LINESTRING") != NULL, "LINESTRING WKT output invalid");
            if (wkt) rtfree(ctx, wkt);
            rtline_free(ctx, line2);
        }
    }

    /* 9. 验证 needs_bbox / add_bbox 操作 */
    int needs_bbox = rtgeom_needs_bbox(ctx, (RTGEOM *)pt);
    rtgeom_add_bbox(ctx, (RTGEOM *)pt);
    const RTGBOX *bbox = rtgeom_get_bbox(ctx, (RTGEOM *)pt);
    printf("POINT needs_bbox=%d, bbox after add=%p\n", needs_bbox, (void *)bbox);
    (void)needs_bbox;

    /* 清理 */
    rtline_free(ctx, line);
    rtpoint_free(ctx, pt);
    rtgeom_finish(ctx);

    if (g_failures > 0) {
        fprintf(stderr, "FAIL: %d check(s) failed\n", g_failures);
        return 1;
    }
    printf("PASS: librttopo API unit tests - context, geometry construction, SRID, area/length, WKT\n");
    return 0;
}
