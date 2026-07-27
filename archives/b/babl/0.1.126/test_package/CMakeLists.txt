cmake_minimum_required(VERSION 3.15)
project(test_babl C)

# Find the package via Conan-generated CMakeDeps
find_package(babl REQUIRED)

add_executable(test_babl test.c)
target_link_libraries(test_babl babl::babl)

enable_testing()
add_test(NAME test_babl COMMAND test_babl)
