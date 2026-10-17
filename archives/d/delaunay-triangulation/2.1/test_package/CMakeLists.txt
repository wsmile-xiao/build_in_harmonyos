cmake_minimum_required(VERSION 3.15)
project(test_delaunay-triangulation CXX)

# Find the package via Conan-generated CMakeDeps
find_package(delaunay-triangulation REQUIRED)

add_executable(test_delaunay-triangulation test.cpp)
target_link_libraries(test_delaunay-triangulation delaunay-triangulation::delaunay-triangulation)

enable_testing()
add_test(NAME test_delaunay-triangulation COMMAND test_delaunay-triangulation)
