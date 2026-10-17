cmake_minimum_required(VERSION 3.15)
project(rulex_consumer C)

find_package(rulex REQUIRED CONFIG)

add_executable(test_rulex test_rulex.c)
target_link_libraries(test_rulex PRIVATE rulex::rulex)
