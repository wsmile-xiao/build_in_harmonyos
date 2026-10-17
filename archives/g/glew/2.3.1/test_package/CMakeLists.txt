cmake_minimum_required(VERSION 3.15)
project(test_glew C)

find_package(glew CONFIG REQUIRED)

add_executable(test_glew test_glew.c)
target_link_libraries(test_glew PRIVATE glew::glew)
