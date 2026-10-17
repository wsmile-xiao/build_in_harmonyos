cmake_minimum_required(VERSION 3.16)
project(test_lightning C)

find_package(lightning REQUIRED)

add_executable(test_lightning test.c)
target_link_libraries(test_lightning PRIVATE lightning::lightning)
