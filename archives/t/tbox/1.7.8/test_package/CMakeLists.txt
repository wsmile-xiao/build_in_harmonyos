cmake_minimum_required(VERSION 3.15)
project(tbox_test LANGUAGES C)

find_package(tbox CONFIG REQUIRED)
add_executable(tbox_test test.c)
target_link_libraries(tbox_test PRIVATE tbox::tbox)
