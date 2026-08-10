cmake_minimum_required(VERSION 3.15)
project(test_potrace C)

# Find the package via Conan-generated CMakeDeps
find_package(potrace REQUIRED)

add_executable(test_potrace test.c)
target_link_libraries(test_potrace potrace::potrace)

enable_testing()
add_test(NAME test_potrace COMMAND test_potrace)
