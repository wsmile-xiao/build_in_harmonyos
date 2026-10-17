#include <geos_c.h>

#include <cmath>
#include <cstdio>
#include <cstring>

static int expect_true(bool condition, const char *message) {
    if (!condition) {
        std::fprintf(stderr, "GEOS test failed: %s\n", message);
        return 1;
    }
    return 0;
}

static int expect_close(double value, double expected, double tolerance,
                        const char *message) {
    return expect_true(std::fabs(value - expected) <= tolerance, message);
}

int main() {
    int failures = 0;
    initGEOS(nullptr, nullptr);

    const char *version = GEOSversion();
    failures += expect_true(version != nullptr &&
                                std::strstr(version, "3.13.0") != nullptr,
                            "GEOSversion reports 3.13.0");

    GEOSGeometry *square = GEOSGeomFromWKT(
        "POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))");
    failures += expect_true(square != nullptr, "parse WKT polygon");
    if (square == nullptr) {
        finishGEOS();
        return 1;
    }

    double area = 0.0;
    failures += expect_true(GEOSArea(square, &area) == 1, "compute polygon area");
    failures += expect_close(area, 4.0, 1e-9, "polygon area is 4");

    GEOSGeometry *point = GEOSGeomFromWKT("POINT (1 1)");
    failures += expect_true(point != nullptr, "parse WKT point");
    if (point == nullptr) {
        GEOSGeom_destroy(square);
        finishGEOS();
        return 1;
    }

    GEOSGeometry *buffer = GEOSBuffer(point, 1.0, 8);
    failures += expect_true(buffer != nullptr, "create point buffer");
    if (buffer != nullptr) {
        double buffer_area = 0.0;
        failures += expect_true(GEOSArea(buffer, &buffer_area) == 1,
                                "compute buffer area");
        failures += expect_true(buffer_area > 3.0, "buffer area is positive");
    }

    failures += expect_true(GEOSIntersects(square, point) == 1,
                            "point intersects square");

    GEOSGeometry *invalid = GEOSGeomFromWKT("NOT_A_GEOMETRY");
    failures += expect_true(invalid == nullptr, "invalid WKT is rejected");

    GEOSGeom_destroy(square);
    GEOSGeom_destroy(point);
    if (buffer != nullptr) {
        GEOSGeom_destroy(buffer);
    }
    finishGEOS();
    return failures == 0 ? 0 : 1;
}
