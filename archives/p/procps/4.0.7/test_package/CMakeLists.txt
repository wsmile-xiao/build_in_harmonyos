cmake_minimum_required(VERSION 3.15)
project(test_procps C)

find_package(procps REQUIRED)

add_executable(test_procps test_procps.c)
target_link_libraries(test_procps PRIVATE procps::procps)
