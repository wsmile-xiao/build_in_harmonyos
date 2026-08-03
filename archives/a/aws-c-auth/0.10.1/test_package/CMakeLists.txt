cmake_minimum_required(VERSION 3.15)
project(test_aws_c_auth C)

find_package(aws-c-auth REQUIRED)

add_executable(test_aws_c_auth test.c)
target_link_libraries(test_aws_c_auth AWS::aws-c-auth)

enable_testing()
add_test(NAME aws_c_auth_init COMMAND test_aws_c_auth --init)
add_test(NAME aws_c_auth_static_credentials COMMAND test_aws_c_auth --credentials)
