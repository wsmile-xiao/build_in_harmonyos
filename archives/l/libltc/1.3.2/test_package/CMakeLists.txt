cmake_minimum_required(VERSION 3.15)
project(libltc_test C)

find_package(libltc REQUIRED)

add_executable(libltc_test test_ltc.c)
target_link_libraries(libltc_test PRIVATE libltc::libltc)
