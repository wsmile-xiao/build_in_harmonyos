cmake_minimum_required(VERSION 3.15)
project(test_sol2 CXX)

find_package(sol2 CONFIG REQUIRED)

add_executable(test_sol2 test.cpp)
target_link_libraries(test_sol2 PRIVATE sol2::sol2)
set_target_properties(test_sol2 PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
