cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(cjose REQUIRED CONFIG)
find_package(OpenSSL REQUIRED)

add_executable(test_package src/test_package.c)
target_link_libraries(test_package PRIVATE cjose::cjose)
# cjose 公共头暴露 <openssl/*.h>; 显式加传递依赖 include 目录
target_include_directories(test_package PRIVATE ${OpenSSL_INCLUDE_DIRS})
