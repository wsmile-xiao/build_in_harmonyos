cmake_minimum_required(VERSION 3.15)
project(test_gc C)

# Find the gc package via Conan-generated CMakeDeps
find_package(gc REQUIRED)

add_executable(test_gc test.c)
target_link_libraries(test_gc gc::gc)

enable_testing()
add_test(NAME test_gc COMMAND test_gc)
