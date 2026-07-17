cmake_minimum_required(VERSION 3.15)
project(test_aws_c_cal C)

find_package(aws-c-cal REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws_c_cal test.c)
target_link_libraries(test_aws_c_cal AWS::aws-c-cal AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_cal COMMAND test_aws_c_cal)
