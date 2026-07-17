cmake_minimum_required(VERSION 3.15)
project(test_aws_c_http C)

find_package(aws-c-http REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-compression REQUIRED)
find_package(aws-c-io REQUIRED)

add_executable(test_aws_c_http test.c)
target_link_libraries(test_aws_c_http aws-c-http::aws-c-http AWS::aws-c-common AWS::aws-c-cal AWS::aws-c-compression AWS::aws-c-io)

enable_testing()
add_test(NAME test_aws_c_http COMMAND test_aws_c_http)
