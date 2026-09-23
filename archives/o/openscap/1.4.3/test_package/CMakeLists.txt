cmake_minimum_required(VERSION 3.15)
project(test_openscap C)

# Find the package via Conan-generated CMakeDeps
find_package(openscap REQUIRED)

add_executable(test_openscap test.c)
target_link_libraries(test_openscap openscap::openscap)

enable_testing()
add_test(NAME test_openscap COMMAND test_openscap)
