cmake_minimum_required(VERSION 3.15)
project(test_c3c C)

# Find the package via Conan-generated CMakeDeps
find_package(c3c REQUIRED)

add_executable(test_c3c test.c)
target_link_libraries(test_c3c c3c::c3c)

enable_testing()
add_test(NAME test_c3c COMMAND test_c3c)
