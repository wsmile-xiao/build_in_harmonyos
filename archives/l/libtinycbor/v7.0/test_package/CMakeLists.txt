cmake_minimum_required(VERSION 3.15)
project(test_libtinycbor C)

# Find the package via Conan-generated CMakeDeps
find_package(libtinycbor REQUIRED)

add_executable(test_libtinycbor test.c)
target_link_libraries(test_libtinycbor libtinycbor::libtinycbor)

enable_testing()
add_test(NAME test_libtinycbor COMMAND test_libtinycbor)
