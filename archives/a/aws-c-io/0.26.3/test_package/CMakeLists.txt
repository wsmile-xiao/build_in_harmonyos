cmake_minimum_required(VERSION 3.15)
project(test_aws_c_io C)

find_package(aws-c-io REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)

add_executable(test_aws_c_io test.c)
target_link_libraries(test_aws_c_io AWS::aws-c-io AWS::aws-c-common AWS::aws-c-cal)

enable_testing()
add_test(NAME test_aws_c_io COMMAND test_aws_c_io)
