cmake_minimum_required(VERSION 3.15)
project(rnnoise_test C)

find_package(rnnoise REQUIRED)

add_executable(rnnoise_test test.c)
target_link_libraries(rnnoise_test PRIVATE rnnoise::rnnoise)
