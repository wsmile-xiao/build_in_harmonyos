cmake_minimum_required(VERSION 3.15)
project(test_lexbor C)

# Find the package via Conan-generated CMakeDeps
find_package(lexbor REQUIRED)

add_executable(test_lexbor test.c)
target_link_libraries(test_lexbor lexbor::lexbor)

enable_testing()
add_test(NAME test_lexbor COMMAND test_lexbor)
