cmake_minimum_required(VERSION 3.15)
project(test_sfsexp C)

find_package(sfsexp REQUIRED)

add_executable(test_sfsexp test_sfsexp.c)
target_link_libraries(test_sfsexp PRIVATE sfsexp::sfsexp)
