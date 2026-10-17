# mapbox-variant 1.2.0

Mapbox Variant is a header-only alternative to `boost::variant` for C++11 and
C++14. The Conan package installs the six public headers below
`include/mapbox/` and exports the CMake target `mapbox::variant`.

The recipe has no external Conan requirements. The upstream build uses a
bundled Catch header and its Makefile; the OHOS package consumer is compiled
with the profile/toolchain compiler and does not inherit the upstream
Makefile's `-march=native` flag.

Upstream source: https://github.com/mapbox/variant/tree/v1.2.0
