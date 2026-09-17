cmake_minimum_required(VERSION 3.14)
project(zxcvbn-c-test LANGUAGES C)

find_package(zxcvbn-c CONFIG REQUIRED)

add_executable(zxcvbn_test test.c)
target_link_libraries(zxcvbn_test PRIVATE zxcvbn-c::zxcvbn-c)
