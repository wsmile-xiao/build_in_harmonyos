cmake_minimum_required(VERSION 3.15)
project(test_soloud CXX)

find_package(soloud REQUIRED CONFIG)

add_executable(test_soloud test.cpp)
target_link_libraries(test_soloud PRIVATE soloud::soloud)
