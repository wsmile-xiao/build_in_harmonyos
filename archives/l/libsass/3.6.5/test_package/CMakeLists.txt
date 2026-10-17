cmake_minimum_required(VERSION 3.15)
project(test_libsass CXX)

find_package(libsass REQUIRED)

add_executable(test_libsass test.cpp)
target_link_libraries(test_libsass libsass::libsass)
