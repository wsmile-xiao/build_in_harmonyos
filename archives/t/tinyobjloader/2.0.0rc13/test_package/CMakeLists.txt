cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(tinyobjloader CONFIG REQUIRED)

add_executable(test_tinyobjloader test_tinyobjloader.cpp)
target_link_libraries(test_tinyobjloader PRIVATE tinyobjloader::tinyobjloader)
target_compile_features(test_tinyobjloader PRIVATE cxx_std_17)
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cube.obj"
    "${CMAKE_CURRENT_BINARY_DIR}/cube.obj"
    COPYONLY
)
