cmake_minimum_required(VERSION 3.15)
project(test_aws_c_sdkutils C)

find_package(aws-c-sdkutils REQUIRED)

add_executable(test_aws_c_sdkutils test.c)
target_link_libraries(test_aws_c_sdkutils aws-c-sdkutils::aws-c-sdkutils)

enable_testing()
add_test(NAME test_aws_c_sdkutils COMMAND test_aws_c_sdkutils)
