cmake_minimum_required(VERSION 3.15)
project(test_consumer C)

find_package(raygui REQUIRED CONFIG)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE raygui::raygui)
