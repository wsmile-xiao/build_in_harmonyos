cmake_minimum_required(VERSION 3.16)
project(test_sljit C)

find_package(sljit REQUIRED)

add_executable(test_sljit test_sljit.c)
target_link_libraries(test_sljit PRIVATE sljit::sljit)
