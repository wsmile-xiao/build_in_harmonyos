cmake_minimum_required(VERSION 3.15)
project(test_libiconv C)

find_package(libiconv REQUIRED)

add_executable(test_libiconv test.c)
target_link_libraries(test_libiconv libiconv::libiconv)
