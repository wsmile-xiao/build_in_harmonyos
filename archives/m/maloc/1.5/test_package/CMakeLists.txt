cmake_minimum_required(VERSION 3.15)
project(maloc_smoke C)

find_package(maloc CONFIG REQUIRED)

add_executable(maloc_smoke main.c)
target_link_libraries(maloc_smoke PRIVATE maloc::maloc)
