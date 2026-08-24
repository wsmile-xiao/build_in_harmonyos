cmake_minimum_required(VERSION 3.15)
project(test_package C)

# R9: use -j1 (not -j$(nproc)) for OHOS (no mkfifo on HMDFS)
set(CMAKE_BUILD_PARALLEL_LEVEL 1)

find_package(libselinux REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE libselinux::libselinux)