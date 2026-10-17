cmake_minimum_required(VERSION 3.15)
project(test_indent C)

# Find the package via Conan-generated CMakeDeps
find_package(indent REQUIRED)

add_executable(test_indent test.c)
target_link_libraries(test_indent indent::indent)

enable_testing()
add_test(NAME test_indent COMMAND test_indent)
