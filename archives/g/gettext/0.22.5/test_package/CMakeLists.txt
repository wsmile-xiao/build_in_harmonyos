cmake_minimum_required(VERSION 3.15)
project(test_gettext C)

find_package(gettext REQUIRED CONFIG)

add_executable(test_gettext test_gettext.c)
target_link_libraries(test_gettext PRIVATE gettext::libintl)
