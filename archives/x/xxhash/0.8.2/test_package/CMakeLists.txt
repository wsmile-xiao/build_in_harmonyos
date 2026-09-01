cmake_minimum_required(VERSION 3.15)
project(test_xxhash C)

# Find the package via Conan-generated CMakeDeps
find_package(xxhash REQUIRED)

add_executable(test_xxhash test.c)
target_link_libraries(test_xxhash xxhash::xxhash)

enable_testing()
add_test(NAME test_xxhash COMMAND test_xxhash)
