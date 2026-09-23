cmake_minimum_required(VERSION 3.15)
project(test_geographiclib CXX)

# Find the package via Conan-generated CMakeDeps
find_package(GeographicLib REQUIRED CONFIG)

add_executable(test_geographiclib test.cpp)
target_link_libraries(test_geographiclib GeographicLib::GeographicLib)

enable_testing()
add_test(NAME test_geographiclib COMMAND test_geographiclib)