cmake_minimum_required(VERSION 3.15)
project(test_lzsa C)

# Find the package via Conan-generated CMakeDeps
find_package(lzsa REQUIRED)

add_executable(test_lzsa test.c)
target_link_libraries(test_lzsa lzsa::lzsa)

enable_testing()
add_test(NAME test_lzsa COMMAND test_lzsa)
