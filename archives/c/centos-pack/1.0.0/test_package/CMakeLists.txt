cmake_minimum_required(VERSION 3.15)
project(PackageTest CXX)

find_package(centos-pack REQUIRED CONFIG)

add_executable(test_package test.cpp)
target_link_libraries(test_package centos-pack::centos-pack)
