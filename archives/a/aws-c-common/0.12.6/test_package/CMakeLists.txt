cmake_minimum_required(VERSION 3.15)
project(test_aws_c_common C)

find_package(aws-c-common REQUIRED)

add_executable(test_aws_c_common test.c)
target_link_libraries(test_aws_c_common AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_common COMMAND test_aws_c_common)
