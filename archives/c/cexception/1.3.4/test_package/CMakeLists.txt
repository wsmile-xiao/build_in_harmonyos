cmake_minimum_required(VERSION 3.15)
project(test_cexception C)

# Find the package via Conan-generated CMakeDeps
find_package(cexception REQUIRED)

add_executable(test_cexception test.c)
target_link_libraries(test_cexception cexception::cexception)

enable_testing()
add_test(NAME test_cexception COMMAND test_cexception)
