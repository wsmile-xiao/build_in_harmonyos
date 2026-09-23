cmake_minimum_required(VERSION 3.15)
project(test_jansson LANGUAGES C)

find_package(jansson CONFIG REQUIRED)

add_executable(test_jansson test.c)
target_link_libraries(test_jansson PRIVATE jansson::jansson)
