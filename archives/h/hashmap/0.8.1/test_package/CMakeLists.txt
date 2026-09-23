cmake_minimum_required(VERSION 3.15)
project(test_hashmap C)

# Find the package via Conan-generated CMakeDeps
find_package(hashmap REQUIRED)

add_executable(test_hashmap test.c)
target_link_libraries(test_hashmap hashmap::hashmap)

enable_testing()
add_test(NAME test_hashmap COMMAND test_hashmap)
