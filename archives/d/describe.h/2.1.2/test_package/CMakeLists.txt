cmake_minimum_required(VERSION 3.15)
project(test_describe.h C)

# Find the package via Conan-generated CMakeDeps
find_package(describe.h REQUIRED)

add_executable(test_describe.h test.c)
target_link_libraries(test_describe.h describe.h::describe.h)

enable_testing()
add_test(NAME test_describe.h COMMAND test_describe.h)
