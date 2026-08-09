cmake_minimum_required(VERSION 3.15)
project(test_glog CXX)

find_package(glog REQUIRED)

add_executable(test_glog src/main.cpp)
target_link_libraries(test_glog glog::glog)
