cmake_minimum_required(VERSION 3.15)
project(test_vtzero CXX)

find_package(vtzero REQUIRED)

add_executable(test_vtzero test_vtzero.cpp)
target_link_libraries(test_vtzero PRIVATE vtzero::vtzero)
