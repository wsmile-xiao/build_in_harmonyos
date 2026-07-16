cmake_minimum_required(VERSION 3.15)
project(test_primesieve CXX)

find_package(primesieve REQUIRED)

add_executable(test_primesieve test_primesieve.cpp)
target_link_libraries(test_primesieve PRIVATE primesieve::primesieve)
set_target_properties(test_primesieve PROPERTIES CXX_STANDARD 11)
