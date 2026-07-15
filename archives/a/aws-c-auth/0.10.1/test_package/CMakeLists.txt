cmake_minimum_required(VERSION 3.15)
project(test_aws_c_auth C)

find_package(aws-c-auth REQUIRED)

add_executable(test_aws_c_auth test.c)
target_link_libraries(test_aws_c_auth aws-c-auth::aws-c-auth)

enable_testing()
add_test(NAME test_aws_c_auth COMMAND test_aws_c_auth)
