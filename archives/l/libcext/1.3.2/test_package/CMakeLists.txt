cmake_minimum_required(VERSION 3.15)
project(test_cext C)

find_package(libcext REQUIRED)

add_executable(test_cext test_cext.c)
target_link_libraries(test_cext libcext::libcext)
