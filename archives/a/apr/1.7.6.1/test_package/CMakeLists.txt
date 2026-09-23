cmake_minimum_required(VERSION 3.15)
project(apr_consumer C)

find_package(apr CONFIG REQUIRED)
add_executable(test_apr test_apr.c)
target_link_libraries(test_apr PRIVATE apr::apr)
