cmake_minimum_required(VERSION 3.15)
project(juman_consumer C)

find_package(juman REQUIRED)

add_executable(test_juman test_juman.c)
target_link_libraries(test_juman PRIVATE juman::juman)
