cmake_minimum_required(VERSION 3.15)
project(test_charls CXX)

find_package(charls REQUIRED)

add_executable(test_charls test_charls.cpp)
target_link_libraries(test_charls PRIVATE charls::charls)
