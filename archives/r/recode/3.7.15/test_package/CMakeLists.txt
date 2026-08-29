cmake_minimum_required(VERSION 3.15)
project(recode_consumer C)

find_package(recode CONFIG REQUIRED)
add_executable(recode_consumer test.c)
target_link_libraries(recode_consumer PRIVATE recode::recode)
