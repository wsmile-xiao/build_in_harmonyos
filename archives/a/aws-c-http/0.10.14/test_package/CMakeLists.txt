cmake_minimum_required(VERSION 3.15)
project(test_aws_c_http C)

find_package(aws-c-http REQUIRED)

add_executable(test_aws_c_http test.c)
target_link_libraries(test_aws_c_http AWS::aws-c-http)

enable_testing()
add_test(NAME test_aws_c_http COMMAND test_aws_c_http)
