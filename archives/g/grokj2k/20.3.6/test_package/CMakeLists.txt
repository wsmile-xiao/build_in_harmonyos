cmake_minimum_required(VERSION 3.15)
project(test_grokj2k LANGUAGES CXX)

find_package(grokj2k REQUIRED)

add_executable(test_grokj2k test.cpp)
target_link_libraries(test_grokj2k PRIVATE grokj2k::grokj2k)
