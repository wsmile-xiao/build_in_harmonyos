cmake_minimum_required(VERSION 3.15)
project(test_aws_c_mqtt C)

find_package(aws-c-mqtt REQUIRED)

add_executable(test_aws_c_mqtt test.c)
target_link_libraries(test_aws_c_mqtt AWS::aws-c-mqtt)

enable_testing()
add_test(NAME test_aws_c_mqtt COMMAND $<TARGET_FILE:test_aws_c_mqtt>)
