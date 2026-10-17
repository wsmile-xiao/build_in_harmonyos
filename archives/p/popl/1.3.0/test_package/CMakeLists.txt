cmake_minimum_required(VERSION 3.15)
project(test_popl CXX)

find_package(popl REQUIRED)

add_executable(test_popl test_popl.cpp)
target_link_libraries(test_popl PRIVATE popl::popl)
