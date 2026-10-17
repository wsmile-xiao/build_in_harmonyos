# mapbox-geometry

Header-only C++14 geometry types (`point`, `line_string`, `polygon`,
`multi_*`, `geometry`, `geometry_collection`, `feature`) for GeoJSON
processing and conversion.

The Conan package installs `include/mapbox/**/*.hpp` and exports the CMake
target `mapbox::geometry`. The enclosing `geometry` type requires
`mapbox-variant`; core point/line_string/polygon types have no dependencies.

Upstream source: https://github.com/mapbox/geometry.hpp/tree/v2.0.3
