cmake_minimum_required(VERSION 3.15)
project(test_cargs C)

# Find the package via Conan-generated CMakeDeps
find_package(cargs REQUIRED)

add_executable(test_cargs test.c)
target_link_libraries(test_cargs cargs::cargs)

enable_testing()
add_test(NAME test_cargs COMMAND test_cargs)
