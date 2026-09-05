cmake_minimum_required(VERSION 3.15)
project(test_hashchop C)

# Find the package via Conan-generated CMakeDeps
find_package(hashchop REQUIRED)

add_executable(test_hashchop test.c)
target_link_libraries(test_hashchop hashchop::hashchop)

enable_testing()
add_test(NAME test_hashchop COMMAND test_hashchop)
