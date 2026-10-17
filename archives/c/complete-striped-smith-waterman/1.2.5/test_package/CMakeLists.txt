cmake_minimum_required(VERSION 3.15)
project(test_complete-striped-smith-waterman C)

# Find the package via Conan-generated CMakeDeps
find_package(complete-striped-smith-waterman REQUIRED)

add_executable(test_complete-striped-smith-waterman test.c)
target_link_libraries(test_complete-striped-smith-waterman complete-striped-smith-waterman::complete-striped-smith-waterman)

enable_testing()
add_test(NAME test_complete-striped-smith-waterman COMMAND test_complete-striped-smith-waterman)
