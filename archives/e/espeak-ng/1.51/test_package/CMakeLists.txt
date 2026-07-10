cmake_minimum_required(VERSION 3.15)
project(test_espeak_ng C)

find_package(espeak-ng REQUIRED)

add_executable(test_espeak_ng test_espeak_ng.c)
target_link_libraries(test_espeak_ng espeak-ng::espeak-ng)

include(CTest)
add_test(NAME test_espeak_ng COMMAND test_espeak_ng)
