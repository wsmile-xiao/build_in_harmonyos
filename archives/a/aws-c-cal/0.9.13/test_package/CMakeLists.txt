cmake_minimum_required(VERSION 3.15)
project(test_aws_c_cal C)

find_package(aws-c-cal REQUIRED)

add_executable(test_aws_c_cal test.c)
target_link_libraries(test_aws_c_cal AWS::aws-c-cal)
