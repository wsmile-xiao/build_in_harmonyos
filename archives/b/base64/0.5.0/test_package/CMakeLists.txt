cmake_minimum_required(VERSION 3.15)
project(test_base64 C)

# Find the package via Conan-generated CMakeDeps
find_package(base64 REQUIRED)

add_executable(test_base64 test.c)
target_link_libraries(test_base64 aklomp::base64)

enable_testing()
add_test(NAME test_base64 COMMAND test_base64)
