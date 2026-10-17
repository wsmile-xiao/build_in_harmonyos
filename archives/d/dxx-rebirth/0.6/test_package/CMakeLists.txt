cmake_minimum_required(VERSION 3.15)
project(dxx_rebirth_consumer C)

find_package(SDL CONFIG REQUIRED)

add_executable(test_sdl_runtime test_sdl_runtime.c)
target_link_libraries(test_sdl_runtime PRIVATE SDL::SDL)
