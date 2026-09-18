cmake_minimum_required(VERSION 3.13)
project(consumer_probe C)

find_package(execs CONFIG REQUIRED)

add_executable(consumer_probe consumer_probe.c)
target_link_libraries(consumer_probe PRIVATE execs::execs)
