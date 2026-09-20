cmake_minimum_required(VERSION 3.15)
project(test_unrar CXX)

find_package(unrar REQUIRED)

add_executable(test_unrar test.cpp)
target_link_libraries(test_unrar unrar::unrar)
