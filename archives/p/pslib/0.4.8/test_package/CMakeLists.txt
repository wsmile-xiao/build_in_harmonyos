cmake_minimum_required(VERSION 3.15)
project(test_pslib C)

find_package(pslib CONFIG REQUIRED)
add_executable(test_pslib test.c)
target_link_libraries(test_pslib PRIVATE pslib::pslib)
