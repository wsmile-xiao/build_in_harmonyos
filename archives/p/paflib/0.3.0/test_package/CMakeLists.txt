cmake_minimum_required(VERSION 3.15)
project(test_paflib C)

find_package(paflib REQUIRED CONFIG)

add_executable(test_paflib test_paflib.c)
target_link_libraries(test_paflib PRIVATE paflib::paflib)
