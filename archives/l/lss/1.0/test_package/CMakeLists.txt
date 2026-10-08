cmake_minimum_required(VERSION 3.15)
project(test_lss C)

find_package(lss REQUIRED)

add_executable(test_lss test.c)
target_link_libraries(test_lss lss::lss)
