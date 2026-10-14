cmake_minimum_required(VERSION 3.15)
project(test_pcp C)

# Find the package via Conan-generated CMakeDeps
find_package(pcp REQUIRED)

add_executable(test_pcp test.c)
target_link_libraries(test_pcp pcp::pcp)

enable_testing()
add_test(NAME test_pcp COMMAND test_pcp)
