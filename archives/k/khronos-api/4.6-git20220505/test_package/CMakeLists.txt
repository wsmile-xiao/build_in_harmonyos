cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(khronos-api CONFIG REQUIRED)

add_executable(test_khronos_api test_khronos_api.c)
target_link_libraries(test_khronos_api PRIVATE khronos-api::khronos-api)
