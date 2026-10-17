cmake_minimum_required(VERSION 3.5)
project(libncl_consumer LANGUAGES CXX)

find_package(libncl REQUIRED CONFIG)
add_executable(test_ncl test.cpp)
target_link_libraries(test_ncl PRIVATE libncl::libncl)
set_target_properties(test_ncl PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
