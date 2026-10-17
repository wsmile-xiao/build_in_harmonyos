cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(aklomp-base64 REQUIRED)

add_executable(test_base64 test.c)
target_link_libraries(test_base64 PRIVATE aklomp-base64::aklomp-base64)
