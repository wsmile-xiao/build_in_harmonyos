#include <mapbox/geojson.hpp>
#include <cassert>
#include <string>

int main() {
    using mapbox::geojson::geojson;
    using mapbox::geojson::geometry;
    using mapbox::geojson::point;

    // Real API usage (R34): parse GeoJSON text into the geometry.hpp
    // representation, inspect the variant, and stringify back.
    const std::string input = R"({"type":"Point","coordinates":[1.0,2.0]})";
    const geojson data = mapbox::geojson::parse(input);
    assert(data.is<geometry>());
    const auto &geom = data.get<geometry>();
    assert(geom.is<point>());
    const auto &pt = geom.get<point>();
    assert(pt.x == 1.0 && pt.y == 2.0);

    const std::string out = mapbox::geojson::stringify(data);
    assert(!out.empty());

    return 0;
}