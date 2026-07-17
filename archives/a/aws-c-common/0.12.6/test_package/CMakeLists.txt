cmake_minimum_required(VERSION 3.15)
project(test_aws_c_common C)

find_package(aws-c-common REQUIRED)
include("${CMAKE_BINARY_DIR}/generators/aws_test_includes.cmake" OPTIONAL)

add_executable(test_aws_c_common test.c)
target_include_directories(test_aws_c_common PRIVATE ${AWS_TEST_INCLUDE_DIRS})
target_link_libraries(test_aws_c_common AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_common COMMAND test_aws_c_common)
