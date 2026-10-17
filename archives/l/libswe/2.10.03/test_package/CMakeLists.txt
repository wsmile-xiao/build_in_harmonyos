cmake_minimum_required(VERSION 3.15)
project(test_swe C)

# Find the package via Conan-generated CMakeDeps
find_package(libswe REQUIRED)

add_executable(test_swe test.c)
target_link_libraries(test_swe libswe::libswe)

enable_testing()
add_test(NAME test_swe COMMAND test_swe)
