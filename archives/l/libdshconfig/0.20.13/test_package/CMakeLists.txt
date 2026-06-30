cmake_minimum_required(VERSION 3.15)
project(test_libdshconfig C)

# Find the package via Conan-generated CMakeDeps
find_package(libdshconfig REQUIRED)

add_executable(test_libdshconfig test.c)
target_link_libraries(test_libdshconfig libdshconfig::libdshconfig)

enable_testing()
add_test(NAME test_libdshconfig COMMAND test_libdshconfig)
