cmake_minimum_required(VERSION 3.15)
project(test_picohttpparser C)

# Locate the package through the Conan-generated CMakeDeps files.
find_package(picohttpparser REQUIRED)

add_executable(test_picohttpparser test.c)
target_link_libraries(test_picohttpparser picohttpparser::picohttpparser)

enable_testing()
add_test(NAME test_picohttpparser COMMAND test_picohttpparser)
