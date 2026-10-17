cmake_minimum_required(VERSION 3.15)
project(opendbxplus_test LANGUAGES CXX)

find_package(libopendbx CONFIG REQUIRED)
find_package(libopendbxplus CONFIG REQUIRED)
add_executable(opendbxplus_test test.cpp)
target_link_libraries(opendbxplus_test PRIVATE libopendbxplus::libopendbxplus)
