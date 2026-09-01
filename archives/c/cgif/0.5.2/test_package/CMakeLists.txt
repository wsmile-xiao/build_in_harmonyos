cmake_minimum_required(VERSION 3.15)
project(test_cgif C)

# Find the package via Conan-generated CMakeDeps
find_package(cgif REQUIRED)

add_executable(test_cgif test.c)
target_link_libraries(test_cgif cgif::cgif)

enable_testing()
add_test(NAME test_cgif COMMAND test_cgif)
