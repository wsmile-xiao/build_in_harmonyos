cmake_minimum_required(VERSION 3.15)
project(smpeg_consumer C)

find_package(smpeg REQUIRED)
# smpeg's public headers include "SDL.h".  The published sdl/1.2.15 package
# ships the SDL headers but declares no cpp_info.includedirs, so the consumer
# has to point at its package folder explicitly (same handling as the
# sdl_mixer/1.2.12 test package).
find_package(SDL CONFIG REQUIRED)

add_executable(test_smpeg test_smpeg.c)
target_include_directories(test_smpeg PRIVATE "${sdl_PACKAGE_FOLDER_RELEASE}/include/SDL")
target_link_libraries(test_smpeg PRIVATE smpeg::smpeg)
