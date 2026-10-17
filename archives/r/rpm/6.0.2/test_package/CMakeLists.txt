cmake_minimum_required(VERSION 3.15)
project(test_rpm C)

find_package(rpm REQUIRED)

add_executable(test_rpm test_rpm.c)
target_link_libraries(test_rpm rpm::rpm)
