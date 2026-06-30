cmake_minimum_required(VERSION 3.15)
project(test_libident C)

# Find the package via Conan-generated CMakeDeps
find_package(libident REQUIRED)

add_executable(test_libident test.c)
target_link_libraries(test_libident libident::libident)

enable_testing()
add_test(NAME test_libident COMMAND test_libident)
