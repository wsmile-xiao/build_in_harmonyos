cmake_minimum_required(VERSION 3.16)
project(test_gtk3 C)

find_package(gtk3 REQUIRED CONFIG)

add_executable(test_gtk3 test_gtk.c)
target_link_libraries(test_gtk3 PRIVATE gtk3::gtk3)
