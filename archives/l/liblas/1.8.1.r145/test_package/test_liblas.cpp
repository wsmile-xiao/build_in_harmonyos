// test_liblas.cpp — consumer test for liblas (Conan L1).
// Exercises real library APIs: version query, Header defaults and
// scale/offset/extent round-trip, Point coordinate storage, Bounds.
#include <liblas/liblas.hpp>
#include <liblas/header.hpp>
#include <liblas/point.hpp>
#include <liblas/bounds.hpp>
#include <liblas/version.hpp>

#undef NDEBUG
#include <cassert>
#include <cmath>
#include <iostream>
#include <string>


// CHECK: NDEBUG-proof assertion. Fails with non-zero exit so the
// harness can catch regressions; passed is only incremented when
// the group really passed.
#define CHECK(cond) do { \
    if (!(cond)) { \
        std::cerr << "CHECK FAILED at line " << __LINE__ << ": " #cond << std::endl; \
        return 1; \
    } \
} while (0)

static bool nearly_equal(double a, double b) {
    return std::fabs(a - b) < 1e-9;
}

int main() {
    int passed = 0;

    // 1. Version string must be non-empty.
    std::string ver = liblas::GetVersion();
    std::string full = liblas::GetFullVersion();
    CHECK(!ver.empty());
    CHECK(!full.empty());
    std::cout << "version: " << full << std::endl;
    ++passed;

    // 2. Default header follows LAS 1.2 with "LASF" signature.
    // Upstream truth (src/header.cpp at r145): the default schema is
    // ePointFormat3, not ePointFormat0, so assert the real default and
    // then round-trip the setter back to format 0.
    liblas::Header header;
    CHECK(header.GetFileSignature() == "LASF");
    CHECK(header.GetVersionMajor() == 1);
    CHECK(header.GetVersionMinor() == 2);
    CHECK(header.GetDataFormatId() == liblas::ePointFormat3);
    header.SetDataFormatId(liblas::ePointFormat0);
    CHECK(header.GetDataFormatId() == liblas::ePointFormat0);
    header.SetDataFormatId(liblas::ePointFormat3);
    CHECK(header.GetDataFormatId() == liblas::ePointFormat3);
    ++passed;

    // 3. Scale round-trip.
    header.SetScale(0.01, 0.01, 0.01);
    CHECK(nearly_equal(header.GetScaleX(), 0.01));
    CHECK(nearly_equal(header.GetScaleY(), 0.01));
    CHECK(nearly_equal(header.GetScaleZ(), 0.01));
    ++passed;

    // 4. Offset round-trip.
    header.SetOffset(100.0, 200.0, 300.0);
    CHECK(nearly_equal(header.GetOffsetX(), 100.0));
    CHECK(nearly_equal(header.GetOffsetY(), 200.0));
    CHECK(nearly_equal(header.GetOffsetZ(), 300.0));
    ++passed;

    // 5. Extent (min/max) round-trip via Bounds.
    header.SetMin(0.0, 0.0, 0.0);
    header.SetMax(100.0, 200.0, 300.0);
    CHECK(nearly_equal(header.GetMinX(), 0.0));
    CHECK(nearly_equal(header.GetMaxX(), 100.0));
    CHECK(nearly_equal(header.GetMinY(), 0.0));
    CHECK(nearly_equal(header.GetMaxY(), 200.0));
    CHECK(nearly_equal(header.GetMinZ(), 0.0));
    CHECK(nearly_equal(header.GetMaxZ(), 300.0));
    const liblas::Bounds<double>& extent = header.GetExtent();
    CHECK(nearly_equal(extent.minx(), 0.0));
    CHECK(nearly_equal(extent.maxz(), 300.0));
    ++passed;

    // 6. Point coordinate storage against the header schema.
    liblas::Point point(&header);
    point.SetCoordinates(1.5, 2.5, 3.5);
    CHECK(nearly_equal(point.GetX(), 1.5));
    CHECK(nearly_equal(point.GetY(), 2.5));
    CHECK(nearly_equal(point.GetZ(), 3.5));
    ++passed;

    // 7. Standalone Bounds arithmetic.
    typedef std::vector<liblas::Range<double> > Ranges;
    Ranges ranges;
    ranges.push_back(liblas::Range<double>(0, 100));
    ranges.push_back(liblas::Range<double>(0, 200));
    ranges.push_back(liblas::Range<double>(0, 300));
    liblas::Bounds<double> bounds(ranges);
    CHECK(nearly_equal(bounds.minx(), 0.0));
    CHECK(nearly_equal(bounds.maxx(), 100.0));
    CHECK(nearly_equal(bounds.maxy(), 200.0));
    CHECK(nearly_equal(bounds.maxz(), 300.0));
    ++passed;

    // 8. Feature flags are queryable (GeoTIFF OFF in this recipe:
    // the conancenter GeoTIFF chain is unbuildable on OHOS, and
    // upstream supports WITH_GEOTIFF=OFF).
    std::cout << "geotiff=" << liblas::IsLibGeoTIFFEnabled()
              << " laszip=" << liblas::IsLasZipEnabled()
              << " gdal=" << liblas::IsGDALEnabled() << std::endl;
    CHECK(liblas::IsLibGeoTIFFEnabled() == false);
    ++passed;

    std::cout << "test_liblas: " << passed << "/8 checks passed" << std::endl;
    return 0;
}
