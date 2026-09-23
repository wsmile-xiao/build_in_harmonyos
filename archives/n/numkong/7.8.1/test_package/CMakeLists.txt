cmake_minimum_required(VERSION 3.15)
project(test_numkong C CXX)

find_package(numkong CONFIG REQUIRED)

add_executable(test_numkong test_package.c)
target_link_libraries(test_numkong PRIVATE numkong::numkong)

# Exercise the header-only path against the installed headers as well.
# numkong.hpp's C++ wrappers require C++20 (concepts / std::integral),
# which matches the upstream nk_test build (CMAKE_CXX_STANDARD 20).
add_executable(test_numkong_headeronly test_headeronly.cpp)
target_link_libraries(test_numkong_headeronly PRIVATE numkong::numkong)
set_target_properties(test_numkong_headeronly PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
