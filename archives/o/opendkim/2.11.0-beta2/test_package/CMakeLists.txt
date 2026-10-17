cmake_minimum_required(VERSION 3.15)
project(test_opendkim C)

# Find the package via Conan-generated CMakeDeps
find_package(opendkim REQUIRED)

add_executable(test_opendkim test.c)
target_link_libraries(test_opendkim opendkim::opendkim)

enable_testing()
add_test(NAME test_opendkim COMMAND test_opendkim)
