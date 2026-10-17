cmake_minimum_required(VERSION 3.15)
project(test_aws_crt CXX)

find_package(aws-crt REQUIRED CONFIG)

add_executable(test_aws_crt test.cpp)
target_link_libraries(test_aws_crt PRIVATE aws-crt::aws-crt)

enable_testing()
add_test(NAME aws_crt_consumer_checks COMMAND test_aws_crt)
