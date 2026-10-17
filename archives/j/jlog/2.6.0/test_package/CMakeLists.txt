cmake_minimum_required(VERSION 3.15)
project(jlog_test_package C)

find_package(jlog CONFIG REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE jlog::jlog)
