cmake_minimum_required(VERSION 3.15)
project(test_bdw-gc C)

# Find the package via Conan-generated CMakeDeps
find_package(bdw-gc REQUIRED)

add_executable(test_bdw-gc test.c)
target_link_libraries(test_bdw-gc bdw-gc::bdw-gc)

enable_testing()
add_test(NAME test_bdw-gc COMMAND test_bdw-gc)
