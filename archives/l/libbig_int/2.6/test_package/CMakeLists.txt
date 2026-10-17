cmake_minimum_required(VERSION 3.15)
project(test_libbig_int C)

# Find the package via Conan-generated CMakeDeps
find_package(libbig_int REQUIRED)

add_executable(test_libbig_int test.c)
target_link_libraries(test_libbig_int libbig_int::libbig_int)

enable_testing()
add_test(NAME test_libbig_int COMMAND test_libbig_int)