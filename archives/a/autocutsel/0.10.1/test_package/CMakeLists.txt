cmake_minimum_required(VERSION 3.15)
project(test_autocutsel C)

# Find the package via Conan-generated CMakeDeps
find_package(autocutsel REQUIRED)

add_executable(test_autocutsel test.c)
target_link_libraries(test_autocutsel autocutsel::autocutsel)

enable_testing()
add_test(NAME test_autocutsel COMMAND test_autocutsel)
