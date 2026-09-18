cmake_minimum_required(VERSION 3.15)
project(picotcp_test LANGUAGES C)

find_package(picotcp CONFIG REQUIRED)
add_executable(picotcp_test test.c)
target_link_libraries(picotcp_test PRIVATE picotcp::picotcp)
