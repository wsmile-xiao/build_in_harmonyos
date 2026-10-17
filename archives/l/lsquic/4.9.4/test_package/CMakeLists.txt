cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(lsquic REQUIRED)

add_executable(${PROJECT_NAME} src/test_package.c)
# openssl headers/libs come through lsquic's package_info requirements
target_link_libraries(${PROJECT_NAME} PRIVATE lsquic::lsquic)
