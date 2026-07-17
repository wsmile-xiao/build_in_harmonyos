cmake_minimum_required(VERSION 3.15)
project(test_aws_c_io C)

find_package(aws-c-io REQUIRED)

add_executable(test_aws_c_io test.c)
target_link_libraries(test_aws_c_io AWS::aws-c-io)
