cmake_minimum_required(VERSION 3.15)
project(test_lwprintf C)

# Find the package via Conan-generated CMakeDeps
find_package(lwprintf REQUIRED)

add_executable(test_lwprintf test.c)
target_link_libraries(test_lwprintf lwprintf::lwprintf)

enable_testing()
add_test(NAME test_lwprintf COMMAND test_lwprintf)