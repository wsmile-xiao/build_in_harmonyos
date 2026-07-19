cmake_minimum_required(VERSION 3.15)
project(test_aws-c-common C)

# Find the package via Conan-generated CMakeDeps
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-common test.c)
target_link_libraries(test_aws-c-common aws-c-common::aws-c-common)

enable_testing()
add_test(NAME test_aws-c-common COMMAND test_aws-c-common)
