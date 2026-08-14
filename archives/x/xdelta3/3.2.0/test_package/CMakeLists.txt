cmake_minimum_required(VERSION 3.15)
project(test_xdelta3 C)

# Find the xdelta3 package via Conan-generated CMakeDeps
find_package(xdelta3 REQUIRED)

add_executable(test_xdelta3 test.c)
target_link_libraries(test_xdelta3 xdelta3::xdelta3)

enable_testing()
add_test(NAME test_xdelta3 COMMAND test_xdelta3)
