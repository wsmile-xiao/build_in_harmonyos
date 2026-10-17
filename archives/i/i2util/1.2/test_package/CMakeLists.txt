cmake_minimum_required(VERSION 3.15)
project(test_i2util C)

# Find the package via Conan-generated CMakeDeps
find_package(i2util REQUIRED)

add_executable(test_i2util test.c)
target_link_libraries(test_i2util i2util::i2util)

enable_testing()
add_test(NAME test_i2util COMMAND test_i2util)
