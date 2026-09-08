cmake_minimum_required(VERSION 3.15)
project(test_buddy CXX)

find_package(buddy REQUIRED CONFIG)

add_executable(test_buddy test_buddy.cpp)
target_link_libraries(test_buddy PRIVATE buddy::bdd)
