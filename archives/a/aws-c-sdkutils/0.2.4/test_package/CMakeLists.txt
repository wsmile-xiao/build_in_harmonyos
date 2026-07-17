cmake_minimum_required(VERSION 3.15)
project(test_aws_c_sdkutils C)

find_package(aws-c-sdkutils REQUIRED)
find_package(aws-c-common REQUIRED)
include("${CMAKE_BINARY_DIR}/generators/aws_test_includes.cmake" OPTIONAL)

add_executable(test_aws_c_sdkutils test.c)
target_include_directories(test_aws_c_sdkutils PRIVATE ${AWS_TEST_INCLUDE_DIRS})
target_link_libraries(test_aws_c_sdkutils AWS::aws-c-sdkutils AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_sdkutils COMMAND test_aws_c_sdkutils)
