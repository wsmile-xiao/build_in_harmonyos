cmake_minimum_required(VERSION 3.15)
project(test_opendmarc C)

# Find the package via Conan-generated CMakeDeps
find_package(opendmarc REQUIRED)

add_executable(test_opendmarc test.c)
target_link_libraries(test_opendmarc opendmarc::opendmarc)

enable_testing()
add_test(NAME test_opendmarc COMMAND test_opendmarc)
