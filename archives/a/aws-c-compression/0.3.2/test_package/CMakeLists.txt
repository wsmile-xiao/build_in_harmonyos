cmake_minimum_required(VERSION 3.15)
project(test_aws_c_compression C)

find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws_c_compression test.c)
target_link_libraries(test_aws_c_compression AWS::aws-c-compression AWS::aws-c-common)

enable_testing()
add_test(NAME test_aws_c_compression COMMAND test_aws_c_compression)
