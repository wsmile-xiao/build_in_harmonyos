cmake_minimum_required(VERSION 3.16)
project(cpipe_test_package LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

add_executable(test_cpipe_ohos test_cpipe_ohos.c)
