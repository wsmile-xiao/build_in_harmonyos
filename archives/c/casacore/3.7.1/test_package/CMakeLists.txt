cmake_minimum_required(VERSION 3.14)
project(test_casacore CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(casacore REQUIRED)

add_executable(test_casacore test_casacore.cpp)
target_link_libraries(test_casacore casacore::casacore)
