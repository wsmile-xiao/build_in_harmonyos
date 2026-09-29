cmake_minimum_required(VERSION 3.15)
project(test_matrix_hub C)

# Find the package via Conan-generated CMakeDeps
find_package(matrix_hub REQUIRED)

add_executable(test_matrix_hub test.c)
target_link_libraries(test_matrix_hub matrix_hub::matrix_hub)

enable_testing()
add_test(NAME test_matrix_hub COMMAND test_matrix_hub)
