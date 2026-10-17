cmake_minimum_required(VERSION 3.15)
project(test_mcpp C)

find_package(mcpp CONFIG REQUIRED)

add_executable(test_mcpp test.c)
target_link_libraries(test_mcpp mcpp::mcpp)
