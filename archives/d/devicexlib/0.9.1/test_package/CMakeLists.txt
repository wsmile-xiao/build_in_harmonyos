cmake_minimum_required(VERSION 3.15)
project(devicexlib_test C)

find_package(devicexlib REQUIRED)

add_executable(test_devicexlib test.c)
target_link_libraries(test_devicexlib PRIVATE devicexlib::devicexlib)
