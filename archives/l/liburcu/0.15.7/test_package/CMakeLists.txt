cmake_minimum_required(VERSION 3.15)
project(test_liburcu C)

# Find the package via Conan-generated CMakeDeps
find_package(liburcu REQUIRED)

add_executable(test_liburcu test.c)
target_link_libraries(test_liburcu liburcu::liburcu)

enable_testing()
add_test(NAME test_liburcu COMMAND test_liburcu)
