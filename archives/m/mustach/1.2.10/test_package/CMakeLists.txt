cmake_minimum_required(VERSION 3.15)
project(test_mustach C)

find_package(mustach REQUIRED)

add_executable(test_mustach test_mustach.c)
target_link_libraries(test_mustach PRIVATE mustach::mustach)
