#include <mapbox/feature.hpp>
#include <mapbox/geometry.hpp>
#include <mapbox/geometry/envelope.hpp>
#include <mapbox/geometry/for_each_point.hpp>
#include <mapbox/geometry_io.hpp>
#include <mapbox/variant.hpp>

#include <cstdio>
#include <sstream>
#include <string>

int main() {
    int failures = 0;
    int passed = 0;
    auto check = [&](bool cond, const char* name) {
        if (cond) {
            ++passed;
        } else {
            std::printf("FAIL %s\n", name);
            ++failures;
        }
    };

    mapbox::geometry::point<double> pt(1.0, 2.0);
    check(pt.x == 1.0 && pt.y == 2.0, "point init");

    mapbox::geometry::line_string<double> ls{{0.0, 0.0}, {3.0, 4.0}};
    check(ls.size() == 2 && ls[1].x == 3.0, "line_string init");

    mapbox::geometry::polygon<double> poly{{{0.0, 0.0}, {4.0, 0.0}, {4.0, 3.0}, {0.0, 0.0}}};
    check(poly.size() == 1 && poly[0].size() == 4, "polygon init");

    mapbox::geometry::geometry<double> geom(pt);
    check(geom.is<mapbox::geometry::point<double>>() &&
              mapbox::util::get<mapbox::geometry::point<double>>(geom).x == 1.0,
          "geometry variant access");

    mapbox::geometry::geometry_collection<double> gc;
    gc.emplace_back(pt);
    check(gc.size() == 1, "geometry_collection emplace");

    auto box = mapbox::geometry::envelope(poly);
    check(box.min.x == 0.0 && box.max.x == 4.0 && box.max.y == 3.0, "envelope");

    int visits = 0;
    mapbox::geometry::for_each_point(ls, [&](auto const&) { ++visits; });
    check(visits == 2, "for_each_point");

    std::stringstream stream;
    stream << pt;
    check(stream.str() == "[1,2]", "geometry_io output");

    if (failures == 0) {
        std::printf("mapbox-geometry 2.0.3 consumer: 8 assertions passed\n");
    }
    return failures == 0 ? 0 : 1;
}
