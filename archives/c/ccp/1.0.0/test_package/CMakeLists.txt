cmake_minimum_required(VERSION 3.15)
project(test_ccp C)

# Find the package via Conan-generated CMakeDeps
find_package(ccp REQUIRED)

add_executable(test_ccp test.c)
target_link_libraries(test_ccp ccp::ccp)

enable_testing()
add_test(NAME test_ccp COMMAND test_ccp)
