cmake_minimum_required(VERSION 3.15)
project(sdl12_compat_consumer C)

find_package(SDL CONFIG REQUIRED)

add_executable(test_sdl12_compat test_sdl12_compat.c)
target_link_libraries(test_sdl12_compat PRIVATE SDL::SDL)
