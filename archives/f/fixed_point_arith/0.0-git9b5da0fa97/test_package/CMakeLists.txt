cmake_minimum_required(VERSION 3.15)
project(test_fixed_point_arith C)

# Find the package via Conan-generated CMakeDeps
find_package(fixed_point_arith REQUIRED)

add_executable(test_fixed_point_arith test.c)
target_link_libraries(test_fixed_point_arith fixed_point_arith::fixed_point_arith)

enable_testing()
add_test(NAME test_fixed_point_arith COMMAND test_fixed_point_arith)
