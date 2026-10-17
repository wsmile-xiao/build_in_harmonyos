cmake_minimum_required(VERSION 3.15)
project(test_munge C)

find_package(munge REQUIRED)

add_executable(test_munge src/main.c)
target_link_libraries(test_munge munge::munge)
