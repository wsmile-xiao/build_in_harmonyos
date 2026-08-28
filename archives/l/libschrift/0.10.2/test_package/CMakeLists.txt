cmake_minimum_required(VERSION 3.15)
project(libschrift_test LANGUAGES C)

find_package(libschrift CONFIG REQUIRED)

add_executable(libschrift_test test.c)
target_link_libraries(libschrift_test PRIVATE libschrift::libschrift)
