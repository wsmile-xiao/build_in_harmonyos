cmake_minimum_required(VERSION 3.15)
project(test_liquidfun CXX)

find_package(liquidfun REQUIRED CONFIG)

add_executable(test_liquidfun test.cpp)
target_link_libraries(test_liquidfun PRIVATE liquidfun::liquidfun)
