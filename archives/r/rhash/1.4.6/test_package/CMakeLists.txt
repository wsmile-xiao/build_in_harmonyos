cmake_minimum_required(VERSION 3.15)
project(test_rhash C)

# Find the package via Conan-generated CMakeDeps
find_package(rhash REQUIRED)

add_executable(test_rhash test.c)
target_link_libraries(test_rhash rhash::rhash)

enable_testing()
add_test(NAME test_rhash COMMAND test_rhash)
