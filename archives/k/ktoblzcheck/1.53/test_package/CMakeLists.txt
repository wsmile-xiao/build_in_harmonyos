cmake_minimum_required(VERSION 3.15)
project(test_ktoblzcheck CXX)

find_package(ktoblzcheck CONFIG REQUIRED)

add_executable(test_ktoblzcheck test_ktoblzcheck.cpp)
target_link_libraries(test_ktoblzcheck PRIVATE ktoblzcheck::ktoblzcheck)
