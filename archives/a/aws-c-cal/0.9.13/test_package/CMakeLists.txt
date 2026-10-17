cmake_minimum_required(VERSION 3.15)
project(test_aws-c-cal C)

# Find the package and its dependencies via Conan CMakeDeps
find_package(aws-c-cal REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-lc REQUIRED)

add_executable(test_aws-c-cal test.c)
target_link_libraries(test_aws-c-cal
    aws-c-cal::aws-c-cal
    aws-c-common::aws-c-common
    aws-lc::aws-lc
)

enable_testing()
add_test(NAME test_aws-c-cal COMMAND test_aws-c-cal)
