cmake_minimum_required(VERSION 3.15)
project(test_libgd2 C)

find_package(libgd2 CONFIG REQUIRED)

add_executable(test_libgd2 test_libgd2.c)
target_link_libraries(test_libgd2 PRIVATE libgd2::libgd2)
