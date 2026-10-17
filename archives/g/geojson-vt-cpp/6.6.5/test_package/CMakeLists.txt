cmake_minimum_required(VERSION 3.15)
project(test_consumer CXX)

find_package(geojson-vt-cpp CONFIG REQUIRED)

add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer PRIVATE mapbox::geojsonvt)