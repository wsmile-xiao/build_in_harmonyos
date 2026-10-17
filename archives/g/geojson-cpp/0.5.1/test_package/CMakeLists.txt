cmake_minimum_required(VERSION 3.15)
project(test_geojson-cpp CXX)

# Find the package via Conan-generated CMakeDeps. Transitive deps are found
# explicitly (mirroring mapbox-geometry's own test_package) so the consumer
# compile gets every include dir.
find_package(geojson-cpp REQUIRED)
find_package(mapbox-geometry CONFIG REQUIRED)
find_package(mapbox-variant CONFIG REQUIRED)
find_package(RapidJSON CONFIG REQUIRED)

add_executable(test_geojson-cpp test_package.cpp)
target_link_libraries(test_geojson-cpp PRIVATE
    geojson-cpp::geojson-cpp
    mapbox::geometry
    mapbox::variant
    RapidJSON::RapidJSON)
target_compile_features(test_geojson-cpp PRIVATE cxx_std_14)
set_target_properties(test_geojson-cpp PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

enable_testing()
add_test(NAME test_geojson-cpp COMMAND test_geojson-cpp)