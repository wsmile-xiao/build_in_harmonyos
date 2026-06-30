cmake_minimum_required(VERSION 3.15)
project(test_xclip C)

# Find the package via Conan-generated CMakeDeps
find_package(xclip REQUIRED)

add_executable(test_xclip test.c)
target_link_libraries(test_xclip xclip::xclip)

enable_testing()
add_test(NAME test_xclip COMMAND test_xclip)
