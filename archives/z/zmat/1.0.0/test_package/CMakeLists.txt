cmake_minimum_required(VERSION 3.15)
project(test_zmat C)

# Find the package via Conan-generated CMakeDeps
find_package(zmat REQUIRED)

add_executable(test_zmat test.c)
target_link_libraries(test_zmat zmat::zmat)

enable_testing()
add_test(NAME test_zmat COMMAND test_zmat)