cmake_minimum_required(VERSION 3.15)
project(test_cdvar C)

# Find the package via Conan-generated CMakeDeps
find_package(c-dvar REQUIRED)

add_executable(test_cdvar test.c)
target_link_libraries(test_cdvar c-dvar::c-dvar)

enable_testing()
add_test(NAME test_cdvar COMMAND test_cdvar)
