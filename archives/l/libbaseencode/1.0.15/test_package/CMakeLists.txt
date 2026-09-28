cmake_minimum_required(VERSION 3.15)
project(test_libbaseencode C)

# Find the package via Conan-generated CMakeDeps
find_package(libbaseencode REQUIRED)

add_executable(test_libbaseencode test.c)
target_link_libraries(test_libbaseencode baseencode)

enable_testing()
add_test(NAME test_libbaseencode COMMAND test_libbaseencode)
