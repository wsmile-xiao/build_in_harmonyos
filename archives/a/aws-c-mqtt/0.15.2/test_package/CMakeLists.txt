cmake_minimum_required(VERSION 3.15)
project(test_aws_c_mqtt C)

find_package(aws-c-mqtt REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-io REQUIRED)
include("${CMAKE_BINARY_DIR}/generators/aws_test_includes.cmake" OPTIONAL)

add_executable(test_aws_c_mqtt test.c)
target_include_directories(test_aws_c_mqtt PRIVATE ${AWS_TEST_INCLUDE_DIRS})
target_link_libraries(test_aws_c_mqtt aws-c-mqtt::aws-c-mqtt AWS::aws-c-common AWS::aws-c-http AWS::aws-c-io)

enable_testing()
add_test(NAME test_aws_c_mqtt COMMAND test_aws_c_mqtt)
