cmake_minimum_required(VERSION 3.15)
project(test_aws_c_compression C)

find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)
include("${CMAKE_BINARY_DIR}/generators/aws_test_includes.cmake" OPTIONAL)

add_executable(test_aws_c_compression test.c)
target_include_directories(test_aws_c_compression PRIVATE ${AWS_TEST_INCLUDE_DIRS})
target_link_libraries(test_aws_c_compression AWS::aws-c-compression AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_compression COMMAND test_aws_c_compression)
