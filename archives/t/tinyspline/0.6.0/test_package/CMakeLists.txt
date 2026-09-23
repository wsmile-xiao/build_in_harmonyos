cmake_minimum_required(VERSION 3.15)
project(test_tinyspline C)

# Find the package via Conan-generated CMakeDeps
find_package(tinyspline REQUIRED)

add_executable(test_tinyspline test.c)
target_link_libraries(test_tinyspline tinyspline::tinyspline)

enable_testing()
add_test(NAME test_tinyspline COMMAND test_tinyspline)
