cmake_minimum_required(VERSION 3.15)
project(test_wildmidi C)

find_package(wildmidi REQUIRED)

add_executable(test_wildmidi test_wildmidi.c)
target_link_libraries(test_wildmidi PRIVATE wildmidi::wildmidi)
