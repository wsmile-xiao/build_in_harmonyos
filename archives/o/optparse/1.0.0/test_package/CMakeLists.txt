cmake_minimum_required(VERSION 3.15)
project(test_optparse C)

# Find the package via Conan-generated CMakeDeps
find_package(optparse REQUIRED)

add_executable(test_optparse test.c)
target_link_libraries(test_optparse optparse::optparse)

enable_testing()
add_test(NAME test_optparse COMMAND test_optparse)
