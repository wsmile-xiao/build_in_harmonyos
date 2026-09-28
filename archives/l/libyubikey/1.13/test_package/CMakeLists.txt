cmake_minimum_required(VERSION 3.15)
project(libyubikey_test LANGUAGES C)

find_package(libyubikey CONFIG REQUIRED)
add_executable(libyubikey_test test.c)
target_link_libraries(libyubikey_test PRIVATE libyubikey::libyubikey)
