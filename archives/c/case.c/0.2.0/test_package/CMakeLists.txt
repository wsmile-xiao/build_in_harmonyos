cmake_minimum_required(VERSION 3.15)
project(test_case.c C)

# Find the package via Conan-generated CMakeDeps
find_package(case.c REQUIRED)

add_executable(test_case.c test.c)
target_link_libraries(test_case.c case.c::case.c)

enable_testing()
add_test(NAME test_case.c COMMAND test_case.c)
