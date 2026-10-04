cmake_minimum_required(VERSION 3.15)
project(test_libdbusmenu C)

find_package(libdbusmenu-gtk3 REQUIRED CONFIG)

add_executable(test_libdbusmenu test_libdbusmenu.c)
target_link_libraries(test_libdbusmenu PRIVATE libdbusmenu-gtk3::libdbusmenu-gtk3)
