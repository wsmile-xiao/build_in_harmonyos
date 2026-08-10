cmake_minimum_required(VERSION 3.15)
project(test_libconfig C)

# Find the package via Conan-generated CMakeDeps
find_package(libconfig REQUIRED)

add_executable(test_libconfig test.c)
target_link_libraries(test_libconfig libconfig::libconfig)

enable_testing()
add_test(NAME test_libconfig COMMAND test_libconfig)
