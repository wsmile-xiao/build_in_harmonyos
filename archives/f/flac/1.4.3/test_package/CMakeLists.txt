cmake_minimum_required(VERSION 3.15)
project(test_flac C)

find_package(flac CONFIG REQUIRED)

add_executable(test_flac test.c)
target_link_libraries(test_flac PRIVATE flac::flac)
