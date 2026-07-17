cmake_minimum_required(VERSION 3.15)
project(test_aws_c_mqtt C)

find_package(aws-c-mqtt REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-io REQUIRED)

add_executable(test_aws_c_mqtt test.c)
target_link_libraries(test_aws_c_mqtt aws-c-mqtt::aws-c-mqtt AWS::aws-c-common aws-c-http::aws-c-http AWS::aws-c-io)

enable_testing()
add_test(NAME test_aws_c_mqtt COMMAND test_aws_c_mqtt)
