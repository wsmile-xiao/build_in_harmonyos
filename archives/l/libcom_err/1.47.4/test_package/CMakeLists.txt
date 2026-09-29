cmake_minimum_required(VERSION 3.15)
project(com_err_consumer_test C)

find_package(com_err CONFIG REQUIRED)

add_executable(test_com_err test_com_err.c)
target_link_libraries(test_com_err com_err::com_err)
