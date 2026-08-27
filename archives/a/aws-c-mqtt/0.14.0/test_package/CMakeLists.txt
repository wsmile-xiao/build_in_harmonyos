cmake_minimum_required(VERSION 3.15)
project(test_aws-c-mqtt C)

find_package(aws-c-mqtt REQUIRED)

add_executable(test_aws-c-mqtt test.c)
target_link_libraries(test_aws-c-mqtt AWS::aws-c-mqtt)

enable_testing()
add_test(NAME test_aws-c-mqtt COMMAND test_aws-c-mqtt)
