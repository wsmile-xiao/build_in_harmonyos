cmake_minimum_required(VERSION 3.15)
project(qd_test_package LANGUAGES CXX)

find_package(qd CONFIG REQUIRED)
add_executable(qd_test_package test_qd.cpp)
target_link_libraries(qd_test_package PRIVATE qd::qd)
