#include <librttopo.h>
#include <librttopo_geom.h>

#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failures = 0;

static void check(int condition, const char *message) {
    g_checks++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        g_failures++;
    }
}

static int split_part_count(const RTCTX *ctx, double offset) {
    RTPOINTARRAY *line_points = NULL;
    RTPOINTARRAY *blade_points = NULL;
    RTLINE *line = NULL;
    RTPOINT *blade = NULL;
    RTGEOM *split = NULL;
    RTCOLLECTION *collection = NULL;
    RTPOINT4D point;
    int parts = -1;

    line_points = ptarray_construct(ctx, 0, 0, 2);
    blade_points = ptarray_construct(ctx, 0, 0, 1);
    if (line_points == NULL || blade_points == NULL) {
        goto cleanup;
    }

    point.x = 0.0;
    point.y = 0.0;
    point.z = 0.0;
    point.m = 0.0;
    ptarray_set_point4d(ctx, line_points, 0, &point);
    point.x = 10.0;
    ptarray_set_point4d(ctx, line_points, 1, &point);
    point.x = 5.0;
    point.y = offset;
    ptarray_set_point4d(ctx, blade_points, 0, &point);

    line = rtline_construct(ctx, 4326, NULL, line_points);
    line_points = NULL;
    blade = rtpoint_construct(ctx, 4326, NULL, blade_points);
    blade_points = NULL;
    if (line == NULL || blade == NULL) {
        goto cleanup;
    }

    split = rtgeom_split(ctx, (const RTGEOM *)line, (const RTGEOM *)blade);
    if (split == NULL) {
        goto cleanup;
    }
    collection = rtgeom_as_rtcollection(ctx, split);
    if (collection != NULL) {
        parts = rtcollection_ngeoms(ctx, collection);
    }

cleanup:
    if (split != NULL) {
        rtgeom_free(ctx, split);
    }
    if (blade != NULL) {
        rtpoint_free(ctx, blade);
    }
    if (line != NULL) {
        rtline_free(ctx, line);
    }
    if (blade_points != NULL) {
        ptarray_free(ctx, blade_points);
    }
    if (line_points != NULL) {
        ptarray_free(ctx, line_points);
    }
    return parts;
}

int main(void) {
    const char *version;
    RTCTX *ctx;
    RTPOINT *point;
    RTLINE *line;
    RTPOINTARRAY *point_array;
    RTPOINTARRAY *line_array;
    RTPOINT4D coordinate;
    RTPOINT *coordinate_point;
    RTLINE *coordinate_line;
    char *wkt;
    int parts;

    version = rtgeom_version();
    check(version != NULL, "rtgeom_version returned NULL");

    ctx = rtgeom_init(NULL, NULL, NULL);
    check(ctx != NULL, "rtgeom_init returned NULL");
    if (ctx == NULL) {
        return 1;
    }

    point = rtpoint_construct_empty(ctx, 4326, 0, 0);
    check(point != NULL, "rtpoint_construct_empty returned NULL");
    if (point == NULL) {
        rtgeom_finish(ctx);
        return 1;
    }

    rtgeom_set_srid(ctx, (RTGEOM *)point, 3857);
    check(rtgeom_get_srid(ctx, (RTGEOM *)point) == 3857,
          "SRID set/get roundtrip failed");

    line = rtline_construct_empty(ctx, 4326, 0, 0);
    check(line != NULL, "rtline_construct_empty returned NULL");
    if (line == NULL) {
        rtpoint_free(ctx, point);
        rtgeom_finish(ctx);
        return 1;
    }

    check(rtgeom_is_collection(ctx, (RTGEOM *)point) == 0 &&
              rtgeom_is_collection(ctx, (RTGEOM *)line) == 0,
          "basic geometry reported as a collection");

    point_array = ptarray_construct(ctx, 0, 0, 1);
    check(point_array != NULL, "point array construction failed");
    coordinate_point = NULL;
    if (point_array != NULL) {
        coordinate.x = 3.0;
        coordinate.y = 4.0;
        coordinate.z = 0.0;
        coordinate.m = 0.0;
        ptarray_set_point4d(ctx, point_array, 0, &coordinate);
        coordinate_point = rtpoint_construct(ctx, 4326, NULL, point_array);
        check(coordinate_point != NULL, "point construction failed");
        if (coordinate_point != NULL) {
            check(rtgeom_area(ctx, (RTGEOM *)coordinate_point) == 0.0,
                  "point area is not zero");
            wkt = rtgeom_to_wkt(
                ctx, (RTGEOM *)coordinate_point, 1, 15, NULL
            );
            check(wkt != NULL && strstr(wkt, "POINT") != NULL,
                  "point WKT output is invalid");
            if (wkt != NULL) {
                rtfree(ctx, wkt);
            }
            rtpoint_free(ctx, coordinate_point);
        }
    }

    line_array = ptarray_construct(ctx, 0, 0, 2);
    check(line_array != NULL, "line array construction failed");
    coordinate_line = NULL;
    if (line_array != NULL) {
        coordinate.x = 0.0;
        coordinate.y = 0.0;
        ptarray_set_point4d(ctx, line_array, 0, &coordinate);
        coordinate.y = 2.0;
        ptarray_set_point4d(ctx, line_array, 1, &coordinate);
        coordinate_line = rtline_construct(ctx, 4326, NULL, line_array);
        check(coordinate_line != NULL, "line construction failed");
        if (coordinate_line != NULL) {
            double length = rtgeom_length(ctx, (RTGEOM *)coordinate_line);
            check(length > 1.999 && length < 2.001,
                  "line length is not two");
            wkt = rtgeom_to_wkt(
                ctx, (RTGEOM *)coordinate_line, 1, 15, NULL
            );
            check(wkt != NULL && strstr(wkt, "LINESTRING") != NULL,
                  "line WKT output is invalid");
            if (wkt != NULL) {
                rtfree(ctx, wkt);
            }
            rtline_free(ctx, coordinate_line);
        }
    }

    parts = split_part_count(ctx, 0.0);
    printf("LIBRTTOPO_SPLIT_EXACT_PARTS=%d\n", parts);
    check(parts == 2, "exact point did not split the line");

    parts = split_part_count(ctx, 5e-13);
    printf("LIBRTTOPO_SPLIT_TOLERANCE_IN_PARTS=%d\n", parts);
    check(parts == 2, "point inside 1e-12 tolerance did not split the line");

    parts = split_part_count(ctx, 2e-12);
    printf("LIBRTTOPO_SPLIT_TOLERANCE_OUT_PARTS=%d\n", parts);
    check(parts == 1, "point outside 1e-12 tolerance split the line");

    rtline_free(ctx, line);
    rtpoint_free(ctx, point);
    rtgeom_finish(ctx);

    if (g_checks != 17) {
        fprintf(stderr, "FAIL: consumer executed %d/17 assertions\n", g_checks);
        return 1;
    }
    if (g_failures != 0) {
        fprintf(stderr, "FAIL: %d/17 consumer assertions failed\n", g_failures);
        return 1;
    }

    printf("LIBRTTOPO_CONSUMER_ASSERTIONS=17/17\n");
    return 0;
}
