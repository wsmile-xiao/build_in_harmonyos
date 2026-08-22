cmake_minimum_required(VERSION 3.15)
project(test_libfm-extra C)

# Find the package via Conan-generated CMakeDeps
find_package(libfm-extra REQUIRED)

add_executable(test_libfm-extra test.c)
target_link_libraries(test_libfm-extra libfm-extra::libfm-extra)

enable_testing()
add_test(NAME test_libfm-extra COMMAND test_libfm-extra)
