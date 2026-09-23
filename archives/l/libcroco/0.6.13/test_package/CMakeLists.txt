cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libcroco REQUIRED)

add_executable(consumer consumer.c)
target_link_libraries(consumer PRIVATE libcroco::libcroco)