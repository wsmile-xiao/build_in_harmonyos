cmake_minimum_required(VERSION 3.15)
project(test_mosquitto C)

find_package(mosquitto REQUIRED)

add_executable(test_mosquitto test.c)
target_link_libraries(test_mosquitto mosquitto::mosquitto)
