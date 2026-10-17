cmake_minimum_required(VERSION 3.15)
project(test_lcms1 C)

# Find the package via Conan-generated CMakeDeps
find_package(lcms1 REQUIRED)

add_executable(test_lcms1 test.c)
target_link_libraries(test_lcms1 lcms1::lcms1)

enable_testing()
add_test(NAME test_lcms1 COMMAND test_lcms1)
