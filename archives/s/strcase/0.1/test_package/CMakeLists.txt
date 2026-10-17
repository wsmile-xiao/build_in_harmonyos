cmake_minimum_required(VERSION 3.15)
project(strcase_test LANGUAGES C)

find_package(strcase CONFIG REQUIRED)
add_executable(strcase_test test.c)
target_link_libraries(strcase_test PRIVATE strcase::strcase)
