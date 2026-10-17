cmake_minimum_required(VERSION 3.15)
project(test_gd C)

# Find the package via Conan-generated CMakeDeps
find_package(gd REQUIRED)

add_executable(test_gd test.c)
target_link_libraries(test_gd gd::gd)

enable_testing()
add_test(NAME test_gd COMMAND test_gd)
