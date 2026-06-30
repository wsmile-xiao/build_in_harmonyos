cmake_minimum_required(VERSION 3.15)
project(test_mynewt-newt C)

# Find the package via Conan-generated CMakeDeps
find_package(mynewt-newt REQUIRED)

add_executable(test_mynewt-newt test.c)
target_link_libraries(test_mynewt-newt mynewt-newt::mynewt-newt)

enable_testing()
add_test(NAME test_mynewt-newt COMMAND test_mynewt-newt)
