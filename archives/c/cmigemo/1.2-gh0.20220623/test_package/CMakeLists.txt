cmake_minimum_required(VERSION 3.15)
project(cmigemo_consumer C)

find_package(cmigemo REQUIRED)

add_executable(consumer test_package.c)
target_link_libraries(consumer PRIVATE cmigemo::cmigemo)
