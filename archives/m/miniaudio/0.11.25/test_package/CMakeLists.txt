cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(miniaudio REQUIRED)

add_executable(test_miniaudio test_miniaudio.c)
target_link_libraries(test_miniaudio PRIVATE miniaudio::miniaudio)
# miniaudio consumers must define MINIAUDIO_IMPLEMENTATION in exactly one
# translation unit to compile the implementation.
target_compile_definitions(test_miniaudio PRIVATE MINIAUDIO_IMPLEMENTATION)
