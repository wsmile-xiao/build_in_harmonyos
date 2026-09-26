cmake_minimum_required(VERSION 3.15)
project(test_arena C)

# Find the package via Conan-generated CMakeDeps
find_package(arena REQUIRED)

add_executable(test_arena test.c)
target_link_libraries(test_arena arena::arena)

enable_testing()
add_test(NAME test_arena COMMAND test_arena)
