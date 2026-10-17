cmake_minimum_required(VERSION 3.15)
project(test_c-algorithms C)

# Find the package via Conan-generated CMakeDeps
find_package(c-algorithms REQUIRED)

add_executable(test_c-algorithms test.c)
target_link_libraries(test_c-algorithms c-algorithms::c-algorithms)

enable_testing()
add_test(NAME test_c-algorithms COMMAND test_c-algorithms)