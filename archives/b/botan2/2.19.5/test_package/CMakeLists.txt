cmake_minimum_required(VERSION 3.15)
project(test_botan2 CXX)

find_package(botan2 REQUIRED CONFIG)

add_executable(test_botan2 test_botan2.cpp)
target_link_libraries(test_botan2 PRIVATE botan2::botan2)

enable_testing()
add_test(NAME botan2_sha256 COMMAND test_botan2)
