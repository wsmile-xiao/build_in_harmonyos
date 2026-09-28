cmake_minimum_required(VERSION 3.15)
project(test_libhbalinux C)

find_package(libhbalinux REQUIRED)

add_executable(test_libhbalinux test_libhbalinux.c)
target_link_libraries(test_libhbalinux PRIVATE libhbalinux::libhbalinux ${CMAKE_DL_LIBS})
