cmake_minimum_required(VERSION 3.13)
project(test_libsbp C)

find_package(libsbp CONFIG REQUIRED)

add_executable(test_libsbp test_libsbp.c)
target_link_libraries(test_libsbp PRIVATE swiftnav::sbp)
