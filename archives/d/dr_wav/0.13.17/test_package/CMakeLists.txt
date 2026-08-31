cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(dr_wav REQUIRED)

add_executable(test_dr_wav test_dr_wav.c)
target_link_libraries(test_dr_wav PRIVATE dr_wav::dr_wav)
# dr_wav consumers must define DR_WAV_IMPLEMENTATION in exactly one
# translation unit to compile the implementation; test_dr_wav.c defines it
# itself above its include.