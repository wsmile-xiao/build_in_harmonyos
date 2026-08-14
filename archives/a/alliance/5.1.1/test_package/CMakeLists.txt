cmake_minimum_required(VERSION 3.15)
project(test_alliance C)

find_package(alliance CONFIG REQUIRED)

add_executable(test_alliance test_alliance.c)
target_link_libraries(test_alliance PRIVATE alliance::alliance)
